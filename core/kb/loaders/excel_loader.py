"""
core/kb/loaders/excel_loader.py
Loader for spreadsheet asset inventories, IP allocations, and customer systems (.xlsx).
"""

from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime, timezone

try:
    import openpyxl
    HAS_OPENPYXL = True
except ImportError:
    HAS_OPENPYXL = False

from core.kb.loaders.base import BaseDataLoader
from core.kb.models import Entity, Provenance
from core.diagnostics import Diagnostics

class ExcelLoader(BaseDataLoader):
    """Loads entities from Excel (.xlsx) workbooks."""

    def load(self, source_path: Path, config: Dict[str, Any]) -> List[Entity]:
        if not HAS_OPENPYXL:
            Diagnostics.warn("openpyxl is not installed; cannot load Excel knowledge sources.")
            return []

        if not source_path.exists():
            Diagnostics.warn(f"Excel source file not found: {source_path}")
            return []

        sheet_name = config.get("sheet")
        id_col = config.get("id_column")
        title_col = config.get("title_column")
        summary_col = config.get("summary_column")
        badge_col = config.get("badge_column")
        severity_col = config.get("severity_column")
        domain = config.get("domain", "internal")
        entity_type = config.get("type", "asset")
        default_severity = config.get("severity", "INFO")
        default_badge = config.get("badge", "ENTERPRISE ASSET")

        wb = openpyxl.load_workbook(source_path, data_only=True, read_only=True)
        sheet = wb[sheet_name] if sheet_name and sheet_name in wb.sheetnames else wb.active

        rows = list(sheet.iter_rows(values_only=True))
        if not rows or len(rows) < 2:
            wb.close()
            return []

        header = [str(cell).strip() if cell is not None else f"col_{idx}" for idx, cell in enumerate(rows[0])]
        header_map = {name.lower(): idx for idx, name in enumerate(header)}

        # Find ID column
        id_idx = None
        if id_col and id_col.lower() in header_map:
            id_idx = header_map[id_col.lower()]
        else:
            # Common fallbacks
            for candidate in ["hostname", "id", "name", "asset", "system", "fqdn"]:
                if candidate in header_map:
                    id_idx = header_map[candidate]
                    break
        if id_idx is None:
            id_idx = 0

        title_idx = header_map.get(title_col.lower()) if title_col else None
        summary_idx = header_map.get(summary_col.lower()) if summary_col else None
        badge_idx = header_map.get(badge_col.lower()) if badge_col else None
        severity_idx = header_map.get(severity_col.lower()) if severity_col else None

        entities: List[Entity] = []

        for row_idx, row in enumerate(rows[1:], start=2):
            if not row or row[id_idx] is None:
                continue

            entity_id = str(row[id_idx]).strip()
            if not entity_id:
                continue

            title = str(row[title_idx]).strip() if title_idx is not None and row[title_idx] is not None else entity_id
            summary = str(row[summary_idx]).strip() if summary_idx is not None and row[summary_idx] is not None else ""
            badge = str(row[badge_idx]).strip() if badge_idx is not None and row[badge_idx] is not None else default_badge
            severity = str(row[severity_idx]).strip().upper() if severity_idx is not None and row[severity_idx] is not None else default_severity

            # Collect attributes from remaining columns
            attributes: Dict[str, Any] = {}
            for col_idx, col_name in enumerate(header):
                if col_idx < len(row) and row[col_idx] is not None:
                    val = row[col_idx]
                    if isinstance(val, (datetime,)):
                        val = val.isoformat()
                    attributes[col_name] = str(val).strip()

            prov = Provenance(
                source=f"excel:{source_path.name}",
                fetched_at=datetime.now(timezone.utc).isoformat(),
                status="resolved",
                manual_override=False,
                details={"sheet": sheet.title, "row": row_idx}
            )

            # Auto-aliases: hostname without domain, ip address if present
            aliases = [entity_id]
            if "." in entity_id:
                aliases.append(entity_id.split(".")[0])
            for attr_k, attr_v in attributes.items():
                if "ip" in attr_k.lower() and attr_v and attr_v not in aliases:
                    aliases.append(attr_v)

            entities.append(Entity(
                id=entity_id,
                domain=domain,
                type=entity_type,
                label=entity_id,
                title=title,
                severity=severity,
                badge=badge,
                summary=summary,
                attributes=attributes,
                references=[],
                provenance=prov,
                aliases=aliases
            ))

        wb.close()
        return entities
