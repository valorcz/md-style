"""
core/kb/loaders/json_loader.py
Loader for structured JSON / YAML network schemas, CMDB dumps, and entity catalogs.
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.kb.loaders.base import BaseDataLoader
from core.kb.models import Entity, Provenance
from core.diagnostics import Diagnostics

class JsonCatalogLoader(BaseDataLoader):
    """Loads entities from JSON or YAML files."""

    def load(self, source_path: Path, config: Dict[str, Any]) -> List[Entity]:
        if not source_path.exists():
            Diagnostics.warn(f"Knowledge file not found: {source_path}")
            return []

        try:
            with open(source_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            Diagnostics.warn(f"Could not read {source_path}: {e}")
            return []

        data: Any = None
        if source_path.suffix.lower() in [".yaml", ".yml"]:
            if HAS_YAML:
                try:
                    data = yaml.safe_load(content)
                except Exception as e:
                    Diagnostics.warn(f"YAML parse error in {source_path}: {e}")
            else:
                Diagnostics.warn("PyYAML not available to parse YAML knowledge.")
        else:
            try:
                data = json.loads(content)
            except Exception as e:
                Diagnostics.warn(f"JSON parse error in {source_path}: {e}")

        if not data:
            return []

        domain = config.get("domain", "internal")
        entity_type = config.get("type", "asset")
        default_severity = config.get("severity", "INFO")

        raw_items: List[Dict[str, Any]] = []
        if isinstance(data, list):
            raw_items = [item for item in data if isinstance(item, dict)]
        elif isinstance(data, dict):
            # If dictionary has "entities" or "items"
            if "entities" in data and isinstance(data["entities"], (list, dict)):
                if isinstance(data["entities"], list):
                    raw_items = data["entities"]
                else:
                    for k, v in data["entities"].items():
                        if isinstance(v, dict):
                            if "id" not in v:
                                v["id"] = k
                            raw_items.append(v)
            elif "items" in data and isinstance(data["items"], list):
                raw_items = data["items"]
            else:
                # Top level dictionary of id -> dict
                for k, v in data.items():
                    if isinstance(v, dict):
                        if "id" not in v:
                            v["id"] = k
                        raw_items.append(v)

        entities: List[Entity] = []
        for idx, item in enumerate(raw_items):
            eid = str(item.get("id") or item.get("name") or f"item-{idx}").strip()
            if not eid:
                continue

            title = str(item.get("title") or eid)
            summary = str(item.get("summary") or item.get("description") or "")
            badge = str(item.get("badge") or "CATALOG ENTITY")
            severity = str(item.get("severity") or default_severity).upper()
            attrs = dict(item.get("attributes") or item.get("fields") or {})
            aliases = list(item.get("aliases") or [eid])

            prov = Provenance(
                source=f"json:{source_path.name}",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                status="resolved",
                manual_override=bool(item.get("manual_override", False)),
                details={"index": idx}
            )

            entities.append(Entity(
                id=eid,
                domain=str(item.get("domain") or domain),
                type=str(item.get("type") or entity_type),
                label=str(item.get("label") or eid),
                title=title,
                severity=severity,
                badge=badge,
                summary=summary,
                attributes=attrs,
                references=list(item.get("references") or item.get("pivots") or []),
                provenance=prov,
                aliases=aliases
            ))

        return entities
