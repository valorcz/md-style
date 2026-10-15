"""
core/kb/resolvers/evtx_resolver.py
Dedicated resolver for Windows Event Log channels (.evtx) and forensic log providers.
Loads authoritative channel metadata directly from data/windows-events.json (SSOT)
with disk caching and dynamic MS Learn fallback lookup.
"""

import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import WIN_EVENTS_DB_PATH, WIN_EVENTS_CACHE_PATH, EVTX_CACHE_PATH
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

EVTX_FILE_REGEX = re.compile(
    r"\b([a-zA-Z0-9_\.\-]+(?:[/\\][a-zA-Z0-9_\.\-]+)*\.evtx)\b",
    re.IGNORECASE
)

# Generic Windows dictionary words that should NEVER match as bare EVTX channels without .evtx extension or channel slash
GENERIC_EVTX_STOPWORDS = {
    "system", "defender", "security", "application", "firewall",
    "operational", "dns", "usb", "vhd", "sam", "lsa", "lsass"
}


def normalize_evtx_token(token: str) -> tuple[str, str, str]:
    """
    Normalizes any EVTX path, filename, or channel token across POSIX and Windows.
    Returns (normalized_path, filename, stem):
      - normalized_path: forward-slash normalized string with environment prefixes stripped.
      - filename: e.g. 'Sysmon.evtx'
      - stem: e.g. 'Sysmon'
    """
    raw = token.strip()
    # Replace backslashes with forward slashes
    norm = raw.replace("\\", "/")
    # Remove surrounding quotes if any
    norm = norm.strip("\"'")
    # Remove leading drive letters like C:/ or %SystemRoot%/ or %SystemDrive%/
    norm = re.sub(r"^(?:[a-zA-Z]:|%[a-zA-Z0-9_]+%)/+", "", norm, flags=re.IGNORECASE)
    # Strip standard winevt logs directory prefix if present
    norm = re.sub(r"^(?:windows/)?system32/winevt/logs/+", "", norm, flags=re.IGNORECASE)

    # Decode URL-encoded characters (e.g. %4 -> /, %20 -> space)
    unquoted = urllib.parse.unquote(norm.replace("%4", "/"))

    filename = norm.split("/")[-1]
    if filename.lower().endswith(".evtx"):
        stem = filename[:-5]
    else:
        stem = filename
        filename = f"{filename}.evtx"

    return norm, filename, stem


class EvtxResolver(BaseResolver):
    name = "evtx"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        cache_file: Path = EVTX_CACHE_PATH,
        catalog: Optional[I18nCatalog] = None
    ):
        if db_path is not None:
            self.db_path = db_path
        elif WIN_EVENTS_CACHE_PATH.exists():
            self.db_path = WIN_EVENTS_CACHE_PATH
        else:
            self.db_path = WIN_EVENTS_DB_PATH

        self.cache_file = cache_file
        self.catalog = catalog or I18nCatalog("en")
        self.db: Dict[str, Any] = {}
        self._lookup: Dict[str, Dict[str, Any]] = {}
        self.online_cache: Dict[str, Any] = {}

        self._load_catalog()
        self._load_online_cache()

    def _load_catalog(self) -> None:
        """Loads channels from unified windows-events.json database."""
        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                raw_data = json.load(f)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to read windows events database: {e}")
            return

        for key, entry in raw_data.items():
            if not isinstance(entry, dict):
                continue
            is_evtx = entry.get("type") == "evtx" or "path" in entry or "channel" in entry or key.lower().endswith(".evtx")
            if not is_evtx:
                continue

            self.db[key] = entry
            # Populate normalized lookup table for fast O(1) matching
            self._register_lookup(key, entry)
            if entry.get("channel"):
                self._register_lookup(entry["channel"], entry)
            if entry.get("id"):
                self._register_lookup(entry["id"], entry)
            if entry.get("path"):
                self._register_lookup(entry["path"], entry)

    def _register_lookup(self, text: str, entry: Dict[str, Any]) -> None:
        raw = text.strip()
        low = raw.lower()
        clean = re.sub(r"[^a-z0-9]", "", low)

        self._lookup[low] = entry
        self._lookup[clean] = entry

        # Normalized path variants
        norm, filename, stem = normalize_evtx_token(raw)
        self._lookup[norm.lower()] = entry
        self._lookup[filename.lower()] = entry
        self._lookup[re.sub(r"[^a-z0-9]", "", filename.lower())] = entry
        if stem.lower() not in GENERIC_EVTX_STOPWORDS:
            self._lookup[stem.lower()] = entry
            self._lookup[re.sub(r"[^a-z0-9]", "", stem.lower())] = entry

        # Unquoted channel name variants (e.g. %4 -> /)
        if "%4" in raw or "%20" in raw:
            unquoted = urllib.parse.unquote(raw.replace("%4", "/")).lower()
            self._lookup[unquoted] = entry
            self._lookup[re.sub(r"[^a-z0-9]", "", unquoted)] = entry

    def _load_online_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.online_cache = json.load(f)
            except Exception:
                self.online_cache = {}

    def _save_online_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.online_cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        low = t.lower()

        # Reject generic English stopwords if not explicitly qualified with .evtx or directory slash
        is_bare = not (low.endswith(".evtx") or "/" in t or "\\" in t)
        if is_bare and low in GENERIC_EVTX_STOPWORDS:
            return False

        if EVTX_FILE_REGEX.fullmatch(t):
            return True
        if low in self._lookup:
            return True
        clean = re.sub(r"[^a-z0-9]", "", low)
        if clean in self._lookup:
            return True
        _, filename, stem = normalize_evtx_token(t)
        if not is_bare and (filename.lower() in self._lookup or stem.lower() in self._lookup):
            return True
        return False

    def extract_candidates(self, text: str) -> List[str]:
        results = []
        for m in EVTX_FILE_REGEX.finditer(text):
            results.append(m.group(0))
        return list(set(results))

    def _find_channel(self, token: str) -> Optional[Dict[str, Any]]:
        t = token.strip()
        # Direct key lookup
        if t in self.db and (self.db[t].get("type") == "evtx" or "channel" in self.db[t]):
            return self.db[t]

        low = t.lower()
        if low in self._lookup:
            return self._lookup[low]

        clean = re.sub(r"[^a-z0-9]", "", low)
        if clean in self._lookup:
            return self._lookup[clean]

        # Normalized path / filename / stem lookup
        _, filename, stem = normalize_evtx_token(t)
        if filename.lower() in self._lookup:
            return self._lookup[filename.lower()]
        if stem.lower() in self._lookup:
            return self._lookup[stem.lower()]

        clean_stem = re.sub(r"[^a-z0-9]", "", stem.lower())
        if clean_stem in self._lookup:
            return self._lookup[clean_stem]

        return None

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        clean_token = token.strip()
        _, filename, stem = normalize_evtx_token(clean_token)

        # 1. Authoritative Catalog Lookup (data/windows-events.json)
        data = self._find_channel(clean_token)
        if data:
            canonical_id = data.get("id") or filename
            return self._to_entity(clean_token, canonical_id, data, source="catalog:windows-events")

        canonical_key = filename

        # 2. Disk Cache for dynamic lookups
        if not force_refresh and canonical_key in self.online_cache:
            return self._to_entity(clean_token, canonical_key, self.online_cache[canonical_key], source="cache:evtx")

        # Guard: Never query MS Learn online if this is a standard system path or invalid query
        is_system_path = any(x in clean_token.lower() for x in ["winevt", "system32", "%systemroot%"])

        # 3. Online Search via MS Learn API
        if allow_online and not is_system_path:
            online_data = self._fetch_online(canonical_key)
            if online_data:
                self.online_cache[canonical_key] = online_data
                self._save_online_cache()
                return self._to_entity(clean_token, canonical_key, online_data, source="api:ms-learn")

        # 4. Fallback Generic EVTX Record
        fallback_data = {
            "title": f"{stem} Event Log",
            "channel": stem,
            "provider": f"Microsoft-Windows-{stem}",
            "path": rf"%SystemRoot%\System32\Winevt\Logs\{canonical_key}",
            "role": f"Windows Operational Event Log for {stem} component telemetry.",
            "key_events": [],
            "audit_policy": "Inspect event log properties and enable operational auditing.",
            "url": f"https://learn.microsoft.com/en-us/search/?terms={urllib.parse.quote(stem)}+evtx"
        }
        return self._to_entity(clean_token, canonical_key, fallback_data, source="fallback:evtx", unresolved=True)

    def _fetch_online(self, canonical_key: str) -> Optional[Dict[str, Any]]:
        stem = Path(canonical_key).stem
        url = f"https://learn.microsoft.com/api/search?search={urllib.parse.quote(stem)}+evtx+windows+event+log&locale=en-us&$top=1"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/2.0 (EVTX Resolver)",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            results = data.get("results", [])
            if results:
                first = results[0]
                return {
                    "title": first.get("title", f"{stem} Event Log"),
                    "channel": stem,
                    "provider": f"Microsoft-Windows-{stem}",
                    "path": rf"%SystemRoot%\System32\Winevt\Logs\{canonical_key}",
                    "role": first.get("description", f"Windows Event Log channel documentation for {stem}."),
                    "key_events": [],
                    "audit_policy": "Review Microsoft Learn documentation for telemetry recommendations.",
                    "url": first.get("url") or f"https://learn.microsoft.com/en-us/search/?terms={urllib.parse.quote(stem)}"
                }
        except Exception as e:
            Diagnostics.debug_log(f"EVTX MS Learn lookup failed for {canonical_key}: {e}")
        return None

    def _to_entity(
        self,
        token: str,
        canonical_key: str,
        data: Dict[str, Any],
        source: str = "catalog:windows-events",
        unresolved: bool = False
    ) -> Entity:
        stem = Path(canonical_key).stem
        display_label = Path(token).name if token.lower().endswith(".evtx") else token
        badge = self.catalog.t("badges.evtx", default="LOG CHANNEL")

        prov = Provenance(
            source=source,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="unresolved" if unresolved else "resolved",
            manual_override=False
        )

        raw_events = data.get("key_events", [])
        relationships: List[Dict[str, Any]] = []
        for item in raw_events:
            m = re.search(r"\b(\d{1,5})\b", str(item))
            if m:
                eid = m.group(1)
                relationships.append({"target": f"Event-{eid}", "type": "winevent", "relation": "hosts_event"})

        for tactic in data.get("mitre_tactics", []):
            relationships.append({"target": tactic, "type": "mitre", "relation": "monitors_tactic"})

        channel_path = data.get("path") or data.get("channel_path", "")
        role = data.get("role") or data.get("forensic_significance") or data.get("summary", "")
        audit_policy = data.get("audit_policy", "")
        retention = data.get("retention", "")
        channel_name = data.get("channel", stem)
        provider = data.get("provider") or channel_name

        details = {
            "Channel Path": channel_path,
            "Logging Channel": channel_name,
            "Forensic Role": role,
            "Key Event IDs": ", ".join(str(x) for x in raw_events) if raw_events else "None indexed",
            "Audit Policy": audit_policy,
            "Retention Policy": retention
        }

        references = []
        if data.get("url"):
            references.append({"title": "Microsoft Documentation", "url": data["url"]})

        # Populate comprehensive aliases to match paths, filenames, stems, and channel names
        aliases_set = {canonical_key, stem, Path(canonical_key).name, channel_name}
        if token:
            aliases_set.add(token)
            aliases_set.add(token.replace("/", "\\"))
            aliases_set.add(token.replace("\\", "/"))
        if channel_path:
            aliases_set.add(channel_path)
            aliases_set.add(channel_path.replace("/", "\\"))
            aliases_set.add(channel_path.replace("\\", "/"))
            # Without %SystemRoot% prefix
            unrooted = re.sub(r"^%[a-zA-Z0-9_]+%[\\/]+", "", channel_path)
            aliases_set.add(unrooted)
            aliases_set.add(unrooted.replace("/", "\\"))
            aliases_set.add(unrooted.replace("\\", "/"))

        # Clean aliases: remove generic English stopwords that do not end in .evtx
        aliases = sorted(
            list({
                a for a in aliases_set
                if a and len(a.strip()) >= 2 and (a.lower().endswith(".evtx") or "/" in a or "\\" in a or a.lower() not in GENERIC_EVTX_STOPWORDS)
            }),
            key=lambda x: len(x),
            reverse=True
        )

        return Entity(
            id=canonical_key,
            domain="cyber",
            type="evtx",
            label=canonical_key,
            title=data.get("title") or f"{stem} Log Channel",
            severity=data.get("severity", "INFO"),
            badge=badge,
            summary=role,
            attributes={
                "Channel Path": channel_path,
                "Channel Name": channel_name,
                "Provider": provider,
                "Audit Recommendation": audit_policy,
                "Retention": retention
            },
            metrics={"default_format": "Binary XML (.evtx)", "log_scope": "Operating System"},
            classification={
                "channel": channel_name,
                "mitre_tactics": data.get("mitre_tactics", []),
                "log_type": "Windows Event Log"
            },
            details=details,
            relationships=relationships,
            references=references,
            provenance=prov,
            aliases=aliases
        )
