"""
core/kb/resolvers/cve_resolver.py
Vulnerability intelligence resolver for Common Vulnerabilities and Exposures (CVE).
Loads authoritative CVE v5 data from CIRCL / NVD API with local caching,
rich metrics extraction (CVSS vector, attack vector, affected software, CWE names),
and bundled offline seed fallback.
"""

import re
import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import CVE_CACHE_PATH, CVE_DB_PATH, CACHE_DIR
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

CVE_REGEX = re.compile(r"\b(CVE-\d{4}-\d{4,7})\b", re.IGNORECASE)


class CveResolver(BaseResolver):
    name = "cve"

    def __init__(
        self,
        cache_file: Path = CVE_CACHE_PATH,
        db_path: Path = CVE_DB_PATH,
        catalog: Optional[I18nCatalog] = None
    ):
        self.cache_file = cache_file
        self.db_path = db_path
        self.catalog = catalog or I18nCatalog("en")
        self.cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        # 1. Load bundled database (data/cve.json) if present
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.cache.update(json.load(f))
            except Exception as e:
                Diagnostics.debug_log(f"Failed to read bundled CVE database: {e}")

        # 2. Check legacy vulns.json in cache directory if cache_file is not yet populated
        legacy_cache = CACHE_DIR / "vulns.json"
        if legacy_cache.exists():
            try:
                with open(legacy_cache, "r", encoding="utf-8") as f:
                    vulns_data = json.load(f)
                    for k, v in vulns_data.items():
                        if k.upper().startswith("CVE-") and k.upper() not in self.cache:
                            self.cache[k.upper()] = v
            except Exception:
                pass

        # 3. Load user runtime cache (intel/cve.json) which takes highest precedence
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    user_cached = json.load(f)
                    for k, v in user_cached.items():
                        if k in self.cache and self.cache[k].get("cvss") and not v.get("cvss"):
                            continue
                        self.cache[k] = v
            except Exception:
                pass

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to write CVE cache: {e}")

    def can_handle(self, token: str) -> bool:
        return bool(CVE_REGEX.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(CVE_REGEX.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        cve_id = token.strip().upper()

        # Check cache if not forcing refresh and entry is non-empty
        if not force_refresh and cve_id in self.cache:
            cached_data = self.cache[cve_id]
            # Ensure cached data isn't a hollow stub
            if cached_data.get("cvss") or cached_data.get("affected") or cached_data.get("cwe"):
                return self._to_entity(cve_id, cached_data, from_cache=True)

        if not allow_online:
            # In offline mode, return whatever is in cache or a clean fallback
            if cve_id in self.cache:
                return self._to_entity(cve_id, self.cache[cve_id], from_cache=True)
            fallback_obj = {
                "id": cve_id,
                "title": f"Vulnerability {cve_id}",
                "summary": "External CVE advisory record (offline mode).",
                "cvss": None,
                "severity": "HIGH",
                "cwe": "",
                "references": [{"title": "NVD Entry", "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"}]
            }
            return self._to_entity(cve_id, fallback_obj, from_cache=False, unresolved=True)

        # Dynamic online fetch via CIRCL CVE v5 API
        fetched = self._fetch_online(cve_id)
        if fetched:
            self.cache[cve_id] = fetched
            self._save_cache()
            return self._to_entity(cve_id, fetched, from_cache=False)

        # Fallback if fetch failed
        fallback_obj = {
            "id": cve_id,
            "title": f"Vulnerability {cve_id}",
            "summary": "External CVE security advisory.",
            "cvss": None,
            "severity": "HIGH",
            "cwe": "",
            "references": [{"title": "NVD Entry", "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"}]
        }
        return self._to_entity(cve_id, fallback_obj, from_cache=False, unresolved=True)

    def _fetch_online(self, cve_id: str) -> Optional[Dict[str, Any]]:
        url = f"https://vulnerability.circl.lu/api/cve/{cve_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/2.0 (CVE Intelligence Resolver)",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            Diagnostics.debug_log(f"CIRCL CVE lookup failed for {cve_id}: {e}")
            return None

        if not raw or not isinstance(raw, dict):
            return None

        containers = raw.get("containers", {})
        cna = containers.get("cna", {})

        # 1. Summary Description
        summary = ""
        for d in cna.get("descriptions", []):
            if d.get("lang", "").startswith("en") and d.get("value"):
                summary = d["value"].strip()
                break
        if not summary and cna.get("descriptions"):
            summary = cna["descriptions"][0].get("value", "").strip()

        # 2. Affected Software, Vendors & CPEs
        affected_items: List[str] = []
        affected_vendors: Set[str] = set()
        affected_products: Set[str] = set()
        cpe_set: Set[str] = set()

        # Check top-level CIRCL vulnerable_configuration / vulnerable_product
        for raw_cpe in (raw.get("vulnerable_configuration") or []) + (raw.get("vulnerable_product") or []):
            if isinstance(raw_cpe, str) and raw_cpe.startswith("cpe:"):
                cpe_set.add(raw_cpe.strip())

        for aff in cna.get("affected", []):
            vendor = aff.get("vendor", "").strip()
            product = aff.get("product", "").strip()
            if vendor and vendor.lower() != "n/a":
                affected_vendors.add(vendor)
            if product and product.lower() != "n/a":
                affected_products.add(product)

            # Extract explicit CPEs from CNA entry
            for cpe_entry in aff.get("cpes", []):
                if isinstance(cpe_entry, str) and cpe_entry.startswith("cpe:"):
                    cpe_set.add(cpe_entry.strip())
                elif isinstance(cpe_entry, dict) and cpe_entry.get("cpe"):
                    cpe_set.add(str(cpe_entry["cpe"]).strip())

            versions_desc: List[str] = []
            for v in aff.get("versions", []):
                v_start = v.get("version", "").strip()
                v_lte = v.get("lessThanOrEqual") or v.get("lessThan")
                if v_start and v_lte and v_start != v_lte:
                    versions_desc.append(f"{v_start}–{v_lte}")
                elif v_start and v_start.lower() != "unspecified":
                    versions_desc.append(v_start)

            prod_label = f"{vendor} {product}".strip() if vendor and vendor != product else (product or vendor)
            if prod_label:
                if versions_desc:
                    affected_items.append(f"{prod_label} ({', '.join(versions_desc[:3])})")
                else:
                    affected_items.append(prod_label)

                # Synthesize standard CPE 2.3 if none found explicitly
                clean_v = re.sub(r"[^a-zA-Z0-9_\.]+", "_", vendor.lower()).strip("_") or "*"
                clean_p = re.sub(r"[^a-zA-Z0-9_\.]+", "_", product.lower()).strip("_") or "*"
                if clean_v != "*" and clean_p != "*":
                    part = "o" if any(os_kw in clean_p for os_kw in ["os", "windows", "linux", "fortios"]) else "a"
                    synth_cpe = f"cpe:2.3:{part}:{clean_v}:{clean_p}:*:*:*:*:*:*:*"
                    cpe_set.add(synth_cpe)

        # 3. CVSS Metrics (v3.1, v3.0, v4.0)
        cvss_score = None
        severity = "HIGH"
        cvss_vector = ""
        attack_vector = ""
        attack_complexity = ""
        privileges_required = ""
        user_interaction = ""
        scope = ""

        metrics = list(cna.get("metrics", []))
        for adp in containers.get("adp", []):
            metrics.extend(adp.get("metrics", []))
        for m in metrics:
            for k in ["cvssV3_1", "cvssV3_0", "cvssV4_0"]:
                if k in m:
                    cvss_data = m[k]
                    cvss_score = cvss_data.get("baseScore")
                    severity = cvss_data.get("baseSeverity", "HIGH").upper()
                    cvss_vector = cvss_data.get("vectorString", "")
                    attack_vector = cvss_data.get("attackVector", "")
                    attack_complexity = cvss_data.get("attackComplexity", "")
                    privileges_required = cvss_data.get("privilegesRequired", "")
                    user_interaction = cvss_data.get("userInteraction", "")
                    scope = cvss_data.get("scope", "")
                    break
            if cvss_score is not None:
                break

        # 4. Weakness Categorization (CWE)
        cwe_id = ""
        cwe_title = ""
        for prob in cna.get("problemTypes", []):
            for desc in prob.get("descriptions", []):
                if desc.get("cweId"):
                    cwe_id = desc.get("cweId").strip()
                    cwe_title = desc.get("description", "").strip()
                    break
            if cwe_id:
                break

        # 5. Remediation Solutions
        solutions: List[str] = []
        for sol in cna.get("solutions", []):
            if sol.get("value"):
                solutions.append(sol["value"].strip())

        # 6. References & Advisories
        references: List[Dict[str, str]] = []
        seen_urls: Set[str] = set()
        for ref in cna.get("references", []):
            ref_url = ref.get("url", "").strip()
            if ref_url and ref_url not in seen_urls:
                seen_urls.add(ref_url)
                name = ref.get("name")
                if not name:
                    if "advisory" in ref_url.lower() or "fortinet" in ref_url.lower() or "cve" in ref_url.lower():
                        name = "Security Advisory"
                    elif "github.com" in ref_url.lower():
                        name = "GitHub Advisory / Commit"
                    else:
                        name = "Vendor Reference"
                references.append({"title": name, "url": ref_url})

        nvd_url = f"https://nvd.nist.gov/vuln/detail/{cve_id}"
        if nvd_url not in seen_urls:
            references.append({"title": "NVD Vulnerability Detail", "url": nvd_url})

        # 7. Smart Title Synthesis
        raw_title = cna.get("title")
        if raw_title and raw_title.strip() and raw_title.strip().upper() != cve_id:
            title = raw_title.strip()
        else:
            vendor_lead = list(affected_vendors)[0] if affected_vendors else ""
            product_lead = list(affected_products)[0] if affected_products else ""
            prod_prefix = f"{vendor_lead} {product_lead}".strip() if vendor_lead != product_lead else product_lead
            weakness_desc = cwe_title if cwe_title and cwe_title.lower() != "n/a" else ""

            if prod_prefix and weakness_desc:
                title = f"{prod_prefix}: {weakness_desc}"
            elif prod_prefix:
                title = f"{prod_prefix} Security Flaw"
            elif weakness_desc:
                title = f"{weakness_desc} ({cve_id})"
            else:
                title = f"Vulnerability {cve_id}"

        return {
            "id": cve_id,
            "title": title,
            "summary": summary,
            "cvss": cvss_score,
            "severity": severity,
            "cvss_vector": cvss_vector,
            "attack_vector": attack_vector,
            "attack_complexity": attack_complexity,
            "privileges_required": privileges_required,
            "user_interaction": user_interaction,
            "scope": scope,
            "cwe": cwe_id,
            "cwe_title": cwe_title,
            "affected": affected_items,
            "affected_vendors": list(affected_vendors),
            "affected_products": list(affected_products),
            "cpes": sorted(list(cpe_set)),
            "solutions": solutions,
            "references": references[:6]
        }

    def _to_entity(self, cve_id: str, data: Dict[str, Any], from_cache: bool = False, unresolved: bool = False) -> Entity:
        cvss = data.get("cvss")
        cvss_vector = data.get("cvss_vector")
        severity = data.get("severity", "HIGH").upper()
        cwe = data.get("cwe", "")
        cwe_title = data.get("cwe_title", "")
        attack_vector = data.get("attack_vector", "")
        attack_complexity = data.get("attack_complexity", "")
        privileges_required = data.get("privileges_required", "")
        user_interaction = data.get("user_interaction", "")
        affected = data.get("affected", [])
        cpes = list(data.get("cpes") or [])
        if not cpes:
            vendors = data.get("affected_vendors", [])
            products = data.get("affected_products", [])
            for v in vendors:
                for p in products:
                    clean_v = re.sub(r"[^a-zA-Z0-9_\.]+", "_", str(v).lower()).strip("_") or "*"
                    clean_p = re.sub(r"[^a-zA-Z0-9_\.]+", "_", str(p).lower()).strip("_") or "*"
                    if clean_v != "*" and clean_p != "*":
                        part = "o" if any(os_kw in clean_p for os_kw in ["os", "windows", "linux", "fortios"]) else "a"
                        cpes.append(f"cpe:2.3:{part}:{clean_v}:{clean_p}:*:*:*:*:*:*:*")
            cpes = sorted(list(set(cpes)))

        badge = f"CVSS {cvss}" if cvss else "CVE RECORD"

        attrs: Dict[str, str] = {}
        if cvss:
            attrs["CVSS Score"] = f"{cvss} ({severity})"
        if attack_vector:
            remotely = "Network / Remote" if attack_vector == "NETWORK" else attack_vector
            attrs["Attack Vector"] = remotely
        if attack_complexity:
            attrs["Attack Complexity"] = attack_complexity
        if privileges_required:
            attrs["Privileges Required"] = privileges_required
        if user_interaction:
            attrs["User Interaction"] = user_interaction
        if cwe:
            attrs["Weakness"] = f"{cwe}: {cwe_title}" if cwe_title else cwe
        if affected:
            attrs["Affected Software"] = ", ".join(affected[:2])

        metrics: Dict[str, Any] = {}
        if cvss is not None:
            metrics["cvss_score"] = cvss
        if cvss_vector:
            metrics["cvss_vector"] = cvss_vector
        if attack_vector:
            metrics["attack_vector"] = attack_vector
        if attack_complexity:
            metrics["attack_complexity"] = attack_complexity
        if privileges_required:
            metrics["privileges_required"] = privileges_required
        if user_interaction:
            metrics["user_interaction"] = user_interaction

        classification: Dict[str, Any] = {}
        if cwe:
            classification["cwes"] = [cwe]
        if data.get("affected_vendors"):
            classification["vendors"] = data["affected_vendors"]
        if data.get("affected_products"):
            classification["products"] = data["affected_products"]
        if cpes:
            classification["cpes"] = cpes

        details: Dict[str, Any] = {
            "Vulnerability ID": cve_id,
            "CVSS Score": f"{cvss} ({severity})" if cvss else "Unscored",
            "CVSS Vector": cvss_vector if cvss_vector else "Not specified",
            "Attack Vector": attack_vector if attack_vector else "Unknown",
            "Weakness (CWE)": f"{cwe} ({cwe_title})" if cwe_title else (cwe if cwe else "Not categorized"),
            "Affected Software": " | ".join(affected) if affected else "See advisory",
        }
        if cpes:
            details["CPE Identifiers"] = ", ".join(cpes[:4])
        if data.get("solutions"):
            details["Remediation Guidance"] = " | ".join(data["solutions"])

        relationships: List[Dict[str, Any]] = []
        if cwe:
            relationships.append({"target": cwe, "type": "cwe", "relation": "categorized_as"})

        prov = Provenance(
            source="registry:circl-cve",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="cached" if from_cache else ("unresolved" if unresolved else "resolved"),
            manual_override=False
        )

        return Entity(
            id=cve_id,
            domain="cyber",
            type="cve",
            label=cve_id,
            title=data.get("title") or cve_id,
            severity=severity,
            badge=badge,
            summary=data.get("summary") or "",
            attributes=attrs,
            metrics=metrics,
            classification=classification,
            details=details,
            relationships=relationships,
            references=data.get("references", []),
            provenance=prov,
            aliases=[cve_id]
        )
