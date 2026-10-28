"""
core/kb/resolvers/statute_resolver.py
Legal and statutory provisions resolver for Czech legal codes (NOZ, ZOK, Zákon o službách, NV 366/2013 Sb.) and GDPR.
Provides authoritative legal summaries, practical SVJ guidance, and direct links to Zákony pro lidi.
"""

import re
import json
import html
import urllib.request
import urllib.parse
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance, WidgetDescriptor
from core.config import STATUTES_DB_PATH, STATUTES_CACHE_PATH, CONFIG_DIR
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

STATUTE_REGEX = re.compile(
    r"(?:§\s*(\d+[a-z]?)|čl\.\s*(\d+))"
    r"(?:\s*odst\.\s*(\d+))?"
    r"(?:\s*písm\.\s*([a-z]\)))?"
    r"(?:\s*(?:(?:zákona\s*o\s*službách|občanského\s*zákoníku|zákona|zák\.|z\.|nařízení\s*vlády|NV)\s*)?(?:č\.|číslo)?\s*(\d+)/(\d{4})(?:\s*Sb\.)?"
    r"|\s*(?:NOZ|občanského\s*zákoníku|zákona\s*o\s*službách|GDPR|ZoKB|ZOK))?",
    re.IGNORECASE
)


class StatuteResolver(BaseResolver):
    name = "statute"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        cache_path: Optional[Path] = None,
        catalog: Optional[I18nCatalog] = None
    ):
        self.catalog = catalog or I18nCatalog("cs")
        self.db_path = db_path or STATUTES_DB_PATH
        self.cache_path = cache_path or STATUTES_CACHE_PATH
        self.user_config_path = CONFIG_DIR / "statutes.json"

        self.db: Dict[str, Dict[str, Any]] = {}
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load_catalogs()

    def _load_catalogs(self) -> None:
        """
        Loads statutes using 3-tier cascading resolution:
          1. Bundled / curated baseline (data/statutes.json)
          2. Persistent dynamic cache (~/.cache/md-style/intel/statutes.json)
          3. User local customizations (~/.config/md-style/statutes.json)
        """
        # Tier 1: Bundled baseline
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.db = json.load(f)
            except Exception as e:
                Diagnostics.debug_log(f"Failed to load bundled statutes DB: {e}")

        # Tier 2: Cached dynamic lookups
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    self._cache = cached
                    # Cached lookups populate database if not already present
                    for k, v in cached.items():
                        if k not in self.db:
                            self.db[k] = v
            except Exception as e:
                Diagnostics.debug_log(f"Failed to load cached statutes: {e}")

        # Tier 3: User config overrides
        if self.user_config_path.exists():
            try:
                with open(self.user_config_path, "r", encoding="utf-8") as f:
                    user_overrides = json.load(f)
                    self.db.update(user_overrides)
            except Exception as e:
                Diagnostics.debug_log(f"Failed to load user config statutes: {e}")

    def _save_cache(self) -> None:
        """Persists dynamically resolved statutes to intel cache."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to save statutes cache: {e}")

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        return bool(STATUTE_REGEX.search(t))

    def extract_candidates(self, text: str) -> List[str]:
        return [m.group(0) for m in STATUTE_REGEX.finditer(text)]

    def _parse_citation(self, token: str) -> Dict[str, Any]:
        """
        Extracts section, act code, act number/year, and canonical database key.
        """
        cleaned = token.strip()
        m = STATUTE_REGEX.search(cleaned)
        if not m:
            return {}

        sec_num = (m.group(1) or m.group(2) or "").lower()
        sub_odst = (m.group(3) or "").lower()
        sub_pism = (m.group(4) or "").lower()
        act_num = m.group(5)
        act_year = m.group(6)

        # Detect specific acts
        low = cleaned.lower()
        act_code = "2012-89"  # Default to NOZ
        act_name = "Zákon č. 89/2012 Sb., občanský zákoník"
        key = sec_num

        if act_num and act_year:
            act_code = f"{act_year}-{act_num}"
            if act_code == "2013-67":
                key = f"67-{sec_num}"
                act_name = "Zákon č. 67/2013 Sb., o službách"
            elif act_code == "2013-366":
                key = f"nv366-{sec_num}"
                act_name = "Nařízení vlády č. 366/2013 Sb."
            elif act_code == "2012-89":
                key = sec_num
                act_name = "Zákon č. 89/2012 Sb., občanský zákoník"
            else:
                key = f"{act_num}-{act_year}-{sec_num}"
                act_name = f"Zákon č. {act_num}/{act_year} Sb."
        elif "67/2013" in low or "služb" in low:
            act_code = "2013-67"
            key = f"67-{sec_num}"
            act_name = "Zákon č. 67/2013 Sb., o službách"
        elif "366/2013" in low or "nařízení vlády" in low:
            act_code = "2013-366"
            key = f"nv366-{sec_num}"
            act_name = "Nařízení vlády č. 366/2013 Sb."
        elif "gdpr" in low:
            act_code = "gdpr"
            key = f"gdpr-{sec_num}"
            act_name = "Nařízení Evropského parlamentu a Rady (EU) 2016/679 (GDPR)"
        elif "zok" in low:
            act_code = "2012-90"
            key = f"90-{sec_num}"
            act_name = "Zákon č. 90/2012 Sb., o obchodních korporacích"
        elif "zokb" in low or "kybernet" in low:
            act_code = "2014-181"
            key = f"181-{sec_num}"
            act_name = "Zákon č. 181/2014 Sb., o kybernetické bezpečnosti"

        # Check existing catalog keys
        if key in self.db:
            matched_key = key
        elif sec_num in self.db:
            matched_key = sec_num
        else:
            base_digits = re.sub(r"\D", "", sec_num)
            if base_digits in self.db:
                matched_key = base_digits
            else:
                matched_key = key

        return {
            "key": matched_key,
            "sec_num": sec_num,
            "sub_odst": sub_odst,
            "sub_pism": sub_pism,
            "act_code": act_code,
            "act_name": act_name
        }

    def _fetch_from_zakonyprolidi(self, act_code: str, sec_num: str) -> Optional[Dict[str, Any]]:
        """
        Dynamically fetches and parses provision text from Zákony pro lidi.
        """
        if act_code == "gdpr":
            return None

        url = f"https://www.zakonyprolidi.cz/cs/{act_code}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; md-style/1.0; +https://github.com/)"}
        )

        try:
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                if resp.status != 200:
                    return None
                html_bytes = resp.read()
                page = html_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            Diagnostics.debug_log(f"Zákony pro lidi fetch failed for {act_code}: {e}")
            return None

        # Extract act title
        act_title = ""
        m_meta = re.search(r'<meta property="og:description" content="(.*?)"', page)
        if m_meta:
            act_title = m_meta.group(1).strip()
        if not act_title:
            m_title = re.search(r'<title>(.*?)</title>', page, re.DOTALL | re.IGNORECASE)
            if m_title:
                act_title = re.sub(r'\s+', ' ', m_title.group(1)).strip()

        # Extract section
        # Pattern for standard paragraph anchor
        pat = rf'<i id="p{sec_num}"></i></a>(?:&sect;|§)?\s*{sec_num}</p>(.*?)(?=<p class="PARA|<div class="FrBlock"|<div class="Footer"|$)'
        m_sec = re.search(pat, page, re.DOTALL | re.IGNORECASE)

        heading = ""
        summary_text = ""
        if m_sec:
            block = m_sec.group(1)
            # Check for subsection heading
            m_head = re.search(r'<h\d[^>]*>(.*?)</h\d>', block, re.DOTALL | re.IGNORECASE)
            if m_head:
                heading = re.sub(r'<[^>]+>', '', m_head.group(1)).strip()
            clean = re.sub(r'<[^>]+>', ' ', block)
            summary_text = re.sub(r'\s+', ' ', html.unescape(clean)).strip()
        else:
            # Fallback search for anchor
            p_pos = page.find(f'id="p{sec_num}"')
            if p_pos != -1:
                snippet = page[p_pos:p_pos + 1200]
                clean = re.sub(r'<[^>]+>', ' ', snippet)
                summary_text = re.sub(r'\s+', ' ', html.unescape(clean)).strip()

        if not summary_text:
            return None

        # Truncate overly verbose text for drawer readability if necessary
        if len(summary_text) > 600:
            summary_text = summary_text[:597] + "..."

        title = f"§ {sec_num}"
        if heading:
            title += f" - {heading}"
        elif act_title:
            title += f" - {act_title}"

        return {
            "title": title,
            "act": act_title or f"Předpis {act_code}",
            "summary": summary_text,
            "commentary": "Znění ustanovení bylo dynamicky načteno ze sbírky Zákony pro lidi. Upravte v data/statutes.json pro vlastní srozumitelný výklad.",
            "url": f"https://www.zakonyprolidi.cz/cs/{act_code}#p{sec_num}"
        }

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        parsed = self._parse_citation(token)
        if not parsed:
            return None

        key = parsed["key"]
        sec_num = parsed["sec_num"]
        act_code = parsed["act_code"]
        act_name = parsed["act_name"]

        info = None
        if not force_refresh:
            info = self.db.get(key)

        # Dynamic online fetch if unknown
        fetched_online = False
        if not info and allow_online:
            info = self._fetch_from_zakonyprolidi(act_code, sec_num)
            if info:
                fetched_online = True
                self.db[key] = info
                self._cache[key] = info
                self._save_cache()

        # Fallback metadata if still not found
        if not info:
            target_url = f"https://www.zakonyprolidi.cz/cs/{act_code}#p{sec_num}" if act_code != "gdpr" else "https://eur-lex.europa.eu/legal-content/CS/TXT/?uri=CELEX%3A32016R0679"
            info = {
                "title": f"Ustanovení § {sec_num} ({act_name})",
                "act": act_name,
                "summary": f"Odkaz na zákonné ustanovení § {sec_num}. Pro zobrazení plného textu povolte připojení k síti nebo doplňte výklad do data/statutes.json.",
                "commentary": "K tomuto ustanovení není v offline katalogu k dispozici podrobný komentář.",
                "url": target_url
            }

        prov = Provenance(
            source="statute:zakonyprolidi-dynamic" if fetched_online else "statute:czech-legal-code",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved",
            manual_override=False
        )

        refs: List[Dict[str, str]] = []
        if info.get("url"):
            refs.append({"title": info["act"], "url": info["url"]})

        # Build extensible widget descriptors for Svelte drawer
        widgets: List[WidgetDescriptor] = [
            WidgetDescriptor(
                widget_type="tactical_box",
                title=info["title"],
                tone="info",
                data={
                    "description": info["summary"],
                    "code": info.get("commentary", ""),
                    "codeLabel": "Doporučení & Praxe / Výklad"
                }
            ),
            WidgetDescriptor(
                widget_type="attributes_table",
                title="Právní metadata",
                data={
                    "Předpis": info["act"],
                    "Ustanovení": f"§ {sec_num}" if not key.startswith("gdpr") else f"Čl. {sec_num}",
                    "Oblast": "Veřejná správa & Právní řád ČR",
                    "Jurisdikce": "Česká republika / EU",
                    "Zdroj": "Zákony pro lidi (AION CS)" if "zakonyprolidi" in info.get("url", "") else "Oficiální věstník EU"
                }
            )
        ]

        if refs:
            widgets.append(
                WidgetDescriptor(
                    widget_type="references",
                    title="Oficiální znění předpisu",
                    data={"references": refs}
                )
            )

        label_display = f"§ {sec_num}" if not key.startswith("gdpr") else f"Čl. {sec_num} GDPR"

        return Entity(
            id=f"statute-{key}",
            domain="legal",
            type="statute",
            label=label_display,
            title=info["title"],
            severity="INFO",
            badge=self.catalog.t("badges.statute", default="ZÁKONNÉ USTANOVENÍ"),
            summary=info["summary"],
            attributes={
                "Předpis": info["act"],
                "Paragraf": label_display
            },
            references=refs,
            provenance=prov,
            widgets=widgets,
            aliases=[
                f"§ {sec_num}",
                f"§{sec_num}",
                label_display,
                info["title"]
            ]
        )
