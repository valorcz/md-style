"""
tests/test_loaders.py
Unit tests for data loaders (Excel and JSON).
"""

import json
from pathlib import Path
import openpyxl
from core.kb.loaders.excel_loader import ExcelLoader
from core.kb.loaders.json_loader import JsonCatalogLoader

def test_excel_loader(tmp_path):
    xlsx_path = tmp_path / "inventory.xlsx"

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Servers"
    ws.append(["Hostname", "IP Address", "Role", "OS"])
    ws.append(["BOR-AD", "192.168.45.253", "Domain Controller", "Windows Server 2022"])
    ws.append(["FS-01", "192.168.45.20", "File Server", "Debian Linux"])
    wb.save(xlsx_path)

    loader = ExcelLoader()
    entities = loader.load(xlsx_path, {
        "sheet": "Servers",
        "id_column": "Hostname",
        "title_column": "Role"
    })

    assert len(entities) == 2
    dc = next(e for e in entities if e.id == "BOR-AD")
    assert dc.title == "Domain Controller"
    assert dc.attributes.get("IP Address") == "192.168.45.253"
    assert "192.168.45.253" in dc.aliases
    assert dc.provenance.details["row"] == 2

def test_json_loader(tmp_path):
    json_path = tmp_path / "catalog.json"
    data = [
        {"id": "FW-PERIMETER", "title": "Border Firewall", "severity": "HIGH", "badge": "TIER-0"}
    ]
    json_path.write_text(json.dumps(data), encoding="utf-8")

    loader = JsonCatalogLoader()
    entities = loader.load(json_path, {"domain": "network"})

    assert len(entities) == 1
    assert entities[0].id == "FW-PERIMETER"
    assert entities[0].domain == "network"
    assert entities[0].severity == "HIGH"
