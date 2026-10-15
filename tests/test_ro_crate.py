"""
tests/test_ro_crate.py
Comprehensive test suite for RO-Crate (Research Object Crate v1.1) packaging,
manifest generation, evidence bundling, and cryptographic verification.
"""

import json
import zipfile
import pytest
from pathlib import Path

from core.crate import ROCrateBuilder, verify_ro_crate, compute_sha256
from core.kb.models import KnowledgePack, Entity, Provenance
from core.engine import ReportEngine, PipelineConfig


def test_ro_crate_builder_manifest_and_serialization(tmp_path):
    builder = ROCrateBuilder(
        title="Test Investigation Report",
        description="A unit test research object crate",
        author="Analyst J. Doe"
    )

    # 1. Add files
    file1 = tmp_path / "data.csv"
    file1.write_text("id,val\n1,100\n", encoding="utf-8")
    builder.add_file(file1, rel_path="data/data.csv", description="Sample raw data")

    builder.add_file_bytes(
        rel_path="notes.txt",
        data=b"Investigative notes",
        name="Investigative Notes",
        encoding_format="text/plain"
    )

    # 2. Add Knowledge Pack
    pack = KnowledgePack(document_id="test-doc")
    pack.entities["CVE-2024-21413"] = Entity(
        id="CVE-2024-21413",
        domain="threat_intel",
        type="cve",
        label="CVE-2024-21413",
        title="Microsoft Outlook RCE"
    )
    builder.add_knowledge_pack(pack, rel_path="report.kb.json")

    # 3. Generate manifest and verify structure
    manifest = builder.generate_manifest()
    assert manifest["@context"] == "https://w3id.org/ro/crate/1.1/context"

    graph = manifest["@graph"]
    by_id = {n["@id"]: n for n in graph}

    # Descriptors
    assert "ro-crate-metadata.json" in by_id
    assert by_id["ro-crate-metadata.json"]["@type"] == "CreativeWork"
    assert "./" in by_id
    assert by_id["./"]["@type"] == "Dataset"
    assert by_id["./"]["name"] == "Test Investigation Report"

    # Files in hasPart
    has_part_ids = [p["@id"] for p in by_id["./"]["hasPart"]]
    assert "data/data.csv" in has_part_ids
    assert "notes.txt" in has_part_ids
    assert "report.kb.json" in has_part_ids

    # Checksum recorded
    assert by_id["notes.txt"]["sha256"] == compute_sha256(b"Investigative notes")

    # Mentions
    mentions_ids = [m["@id"] for m in by_id["./"]["mentions"]]
    assert "urn:entity:CVE-2024-21413" in mentions_ids

    # 4. Build zip and verify
    zip_path = tmp_path / "test.crate.zip"
    builder.build_zip(zip_path)
    assert zip_path.is_file()

    is_valid, errors = verify_ro_crate(zip_path)
    assert is_valid is True
    assert errors == []


def test_ro_crate_tamper_detection(tmp_path):
    builder = ROCrateBuilder(title="Tamper Test")
    builder.add_file_bytes("file.txt", b"Original content")
    zip_path = tmp_path / "tamper.crate.zip"
    builder.build_zip(zip_path)

    # Verify original is valid
    is_valid, errors = verify_ro_crate(zip_path)
    assert is_valid is True

    # Tamper with file.txt
    tampered_zip = tmp_path / "tampered.crate.zip"
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(tampered_zip, "w") as zout:
            for item in zin.namelist():
                data = zin.read(item)
                if item == "file.txt":
                    data = b"Modified malicious content"
                zout.writestr(item, data)

    is_valid_t, errors_t = verify_ro_crate(tampered_zip)
    assert is_valid_t is False
    assert any("Checksum mismatch" in e and "file.txt" in e for e in errors_t)


def test_ro_crate_missing_payload_detection(tmp_path):
    builder = ROCrateBuilder(title="Missing File Test")
    builder.add_file_bytes("keep.txt", b"keep")
    builder.add_file_bytes("delete_me.txt", b"delete")
    zip_path = tmp_path / "missing.crate.zip"
    builder.build_zip(zip_path)

    # Remove delete_me.txt from the zip
    corrupt_zip = tmp_path / "corrupt.crate.zip"
    with zipfile.ZipFile(zip_path, "r") as zin:
        with zipfile.ZipFile(corrupt_zip, "w") as zout:
            for item in zin.namelist():
                if item != "delete_me.txt":
                    zout.writestr(item, zin.read(item))

    is_valid, errors = verify_ro_crate(corrupt_zip)
    assert is_valid is False
    assert any("Missing crate payload file: 'delete_me.txt'" in e for e in errors)


def test_report_engine_crate_integration(tmp_path):
    doc_path = tmp_path / "case_study.md"
    doc_path.write_text(
        "---\n"
        "title: Case Study Intrusion\n"
        "author: Forensic Investigator\n"
        "---\n\n"
        "# Incident Analysis\n\n"
        "Adversary exploited CVE-2024-21413 and executed T1059.001.\n",
        encoding="utf-8"
    )

    ev_dir = tmp_path / "evidence_files"
    ev_dir.mkdir()
    (ev_dir / "memory.dmp").write_bytes(b"DUMP_PAYLOAD_BYTES")
    (ev_dir / "audit.evtx").write_bytes(b"EVTX_LOG_PAYLOAD")

    out_crate = tmp_path / "case_study.crate.zip"

    cfg = PipelineConfig(
        input_file=doc_path,
        output_file=out_crate,
        generate_crate=True,
        evidence_path=ev_dir,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    result = engine.run()

    assert result.is_file()
    assert result == out_crate

    # Verify crate with verify_ro_crate
    is_valid, errors = verify_ro_crate(out_crate)
    assert is_valid is True
    assert errors == []

    # Inspect contents
    with zipfile.ZipFile(out_crate, "r") as zf:
        names = zf.namelist()
        assert "ro-crate-metadata.json" in names
        assert "report.html" in names
        assert "report.md" in names
        assert "report.kb.json" in names
        assert "evidence/memory.dmp" in names
        assert "evidence/audit.evtx" in names

        # Verify Knowledge Pack contains JSON-LD context
        kb_data = json.loads(zf.read("report.kb.json").decode("utf-8"))
        assert "@context" in kb_data
        assert "@type" in kb_data
        assert "CVE-2024-21413" in kb_data["entities"]
