"""
core/crate.py
Standardized RO-Crate (Research Object Crate v1.1) packaging, serialization,
and cryptographic integrity verification for md-style reports and evidence bundles.
Pure-Python, zero external dependencies (uses standard library zipfile, hashlib, json).
"""

import os
import io
import json
import zipfile
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone

from core.kb.models import KnowledgePack, Entity
from core.diagnostics import Diagnostics

RO_CRATE_CONTEXT = "https://w3id.org/ro/crate/1.1/context"
RO_CRATE_CONFORMS_TO = "https://w3id.org/ro/crate/1.1"


def compute_sha256(data: bytes) -> str:
    """Computes hexadecimal SHA-256 digest for given bytes."""
    return hashlib.sha256(data).hexdigest()


class ROCrateBuilder:
    """
    Constructs an RO-Crate 1.1 compliant research package combining:
      1. Compiled HTML report (self-contained with Svelte viewer or pure HTML)
      2. Original Markdown source document
      3. Knowledge Pack entity database (JSON-LD)
      4. Raw supporting evidence files (PCAP, EVTX logs, PDF contracts, data)
      5. Authoritative ro-crate-metadata.json manifest with SHA-256 checksums
    """

    def __init__(
        self,
        title: str = "Research & Investigation Report",
        description: str = "",
        author: str = "",
        date_published: Optional[str] = None
    ):
        self.title = title
        self.description = description
        self.author = author
        self.date_published = date_published or datetime.now(timezone.utc).isoformat()
        
        # In-memory storage for crate files: rel_path -> (bytes, metadata_dict)
        self.files: Dict[str, Tuple[bytes, Dict[str, Any]]] = {}
        self.knowledge_pack: Optional[KnowledgePack] = None

    def add_file_bytes(
        self,
        rel_path: str,
        data: bytes,
        name: str = "",
        encoding_format: str = "application/octet-stream",
        description: str = ""
    ) -> str:
        """Adds in-memory byte content as a crate file."""
        clean_path = rel_path.replace("\\", "/").lstrip("/")
        sha = compute_sha256(data)
        size = len(data)

        meta = {
            "@id": clean_path,
            "@type": "File",
            "name": name or Path(clean_path).name,
            "encodingFormat": encoding_format,
            "contentSize": str(size),
            "sha256": sha
        }
        if description:
            meta["description"] = description

        self.files[clean_path] = (data, meta)
        return clean_path

    def add_file(
        self,
        source_path: Path,
        rel_path: Optional[str] = None,
        name: str = "",
        encoding_format: str = "",
        description: str = ""
    ) -> str:
        """Adds a file from disk into the crate."""
        if not source_path.is_file():
            raise FileNotFoundError(f"Source file not found: {source_path}")

        target = rel_path or source_path.name
        data = source_path.read_bytes()

        fmt = encoding_format
        if not fmt:
            suf = source_path.suffix.lower()
            mime_types = {
                ".html": "text/html",
                ".md": "text/markdown",
                ".json": "application/json",
                ".pdf": "application/pdf",
                ".txt": "text/plain",
                ".pcap": "application/vnd.tcpdump.pcap",
                ".evtx": "application/octet-stream",
                ".png": "image/png",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".svg": "image/svg+xml"
            }
            fmt = mime_types.get(suf, "application/octet-stream")

        return self.add_file_bytes(
            rel_path=target,
            data=data,
            name=name or source_path.name,
            encoding_format=fmt,
            description=description
        )

    def add_evidence_dir(self, evidence_dir: Path, target_prefix: str = "evidence") -> List[str]:
        """Recursively adds all files from an evidence directory into the crate."""
        added = []
        if not evidence_dir.exists():
            return added

        if evidence_dir.is_file():
            rel = f"{target_prefix}/{evidence_dir.name}"
            self.add_file(evidence_dir, rel_path=rel, description="Supporting evidence file")
            added.append(rel)
            return added

        for root, _, files in os.walk(evidence_dir):
            for file in sorted(files):
                full_path = Path(root) / file
                rel_from_dir = full_path.relative_to(evidence_dir)
                target_rel = f"{target_prefix}/{rel_from_dir.as_posix()}"
                self.add_file(full_path, rel_path=target_rel, description=f"Evidence artifact {file}")
                added.append(target_rel)
        return added

    def add_knowledge_pack(
        self,
        pack: KnowledgePack,
        rel_path: str = "knowledge_pack.json"
    ) -> str:
        """Adds KnowledgePack as a JSON-LD crate artifact."""
        self.knowledge_pack = pack
        raw_json = json.dumps(pack.to_dict(), indent=2, ensure_ascii=False).encode("utf-8")
        return self.add_file_bytes(
            rel_path=rel_path,
            data=raw_json,
            name="Knowledge Pack Entity Database",
            encoding_format="application/ld+json",
            description="Authoritative Knowledge Pack containing resolved entities, provenance, and relationships"
        )

    def generate_manifest(self) -> Dict[str, Any]:
        """
        Generates the standard ro-crate-metadata.json conforming to RO-Crate 1.1 spec.
        """
        graph: List[Dict[str, Any]] = []

        # 1. Metadata Descriptor Entity
        graph.append({
            "@id": "ro-crate-metadata.json",
            "@type": "CreativeWork",
            "conformsTo": {
                "@id": RO_CRATE_CONFORMS_TO
            },
            "about": {
                "@id": "./"
            }
        })

        # 2. File list (hasPart)
        has_part = [{"@id": rel_path} for rel_path in sorted(self.files.keys())]

        # 3. Mentions / Contextual entities from Knowledge Pack
        mentions = []
        context_entities = []
        if self.knowledge_pack:
            for ent_id, ent in self.knowledge_pack.entities.items():
                ent_node = {
                    "@id": f"urn:entity:{ent.id}",
                    "@type": ent.type,
                    "name": ent.title,
                    "description": ent.summary,
                    "identifier": ent.id,
                    "domain": ent.domain,
                    "severity": ent.severity
                }
                if ent.references:
                    ent_node["url"] = [r["url"] for r in ent.references if r.get("url")]
                mentions.append({"@id": f"urn:entity:{ent.id}"})
                context_entities.append(ent_node)

        # 4. Root Dataset Entity
        root_dataset: Dict[str, Any] = {
            "@id": "./",
            "@type": "Dataset",
            "name": self.title,
            "description": self.description or f"RO-Crate report archive for {self.title}",
            "datePublished": self.date_published,
            "hasPart": has_part
        }
        if self.author:
            root_dataset["author"] = {
                "@type": "Person",
                "name": self.author
            }
        if mentions:
            root_dataset["mentions"] = mentions

        graph.append(root_dataset)

        # 5. Add all file entities
        for _, (_, meta) in sorted(self.files.items()):
            graph.append(meta)

        # 6. Add contextual domain entities
        graph.extend(context_entities)

        return {
            "@context": RO_CRATE_CONTEXT,
            "@graph": graph
        }

    def build_zip(self, output_zip_path: Path) -> Path:
        """Serializes the entire RO-Crate into a self-contained .zip archive."""
        manifest = self.generate_manifest()
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

        output_zip_path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            # 1. Write ro-crate-metadata.json at root
            zf.writestr("ro-crate-metadata.json", manifest_bytes)

            # 2. Write all payload files
            for rel_path, (data, _) in sorted(self.files.items()):
                zf.writestr(rel_path, data)

        return output_zip_path

    def build_dir(self, output_dir: Path) -> Path:
        """Serializes the RO-Crate into an unpacked directory structure."""
        manifest = self.generate_manifest()
        manifest_bytes = json.dumps(manifest, indent=2, ensure_ascii=False).encode("utf-8")

        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "ro-crate-metadata.json").write_bytes(manifest_bytes)

        for rel_path, (data, _) in self.files.items():
            dest = output_dir / rel_path
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)

        return output_dir


def verify_ro_crate(crate_path: Path) -> Tuple[bool, List[str]]:
    """
    Verifies the structural and cryptographic integrity of an RO-Crate archive (.zip)
    or directory against its ro-crate-metadata.json manifest.

    Checks:
      1. Presence and JSON-LD validity of ro-crate-metadata.json
      2. Conformance to RO-Crate 1.1 spec
      3. Presence of root Dataset (./)
      4. Existence of all files declared in hasPart
      5. SHA-256 checksum matching for all declared files
    """
def _verify_manifest_and_files(
    manifest_data: Dict[str, Any],
    file_reader: Any,
    file_exists: Any
) -> Tuple[bool, List[str]]:
    """Internal validation of ro-crate-metadata.json and all referenced payload files."""
    errors: List[str] = []

    if not isinstance(manifest_data, dict) or "@graph" not in manifest_data:
        return False, ["Invalid manifest: missing '@graph' array"]

    graph = manifest_data["@graph"]
    by_id = {node.get("@id"): node for node in graph if isinstance(node, dict) and "@id" in node}

    # Verify descriptor
    descriptor = by_id.get("ro-crate-metadata.json")
    if not descriptor:
        errors.append("Manifest missing 'ro-crate-metadata.json' CreativeWork descriptor")
    elif descriptor.get("@type") != "CreativeWork":
        errors.append(f"Descriptor type must be 'CreativeWork', got '{descriptor.get('@type')}'")

    # Verify root dataset
    root_dataset = by_id.get("./")
    if not root_dataset:
        errors.append("Manifest missing root Dataset node with @id './'")
    elif root_dataset.get("@type") != "Dataset":
        errors.append(f"Root node type must be 'Dataset', got '{root_dataset.get('@type')}'")

    # Verify hasPart files
    has_part = root_dataset.get("hasPart", []) if root_dataset else []
    for item in has_part:
        rel_id = item.get("@id") if isinstance(item, dict) else str(item)
        if not rel_id or rel_id.startswith("http://") or rel_id.startswith("https://"):
            continue

        file_node = by_id.get(rel_id)
        if not file_node:
            errors.append(f"File '{rel_id}' in hasPart has no corresponding node in @graph")
            continue

        if not file_exists(rel_id):
            errors.append(f"Missing crate payload file: '{rel_id}'")
            continue

        expected_sha = file_node.get("sha256")
        if expected_sha:
            try:
                actual_bytes = file_reader(rel_id)
                actual_sha = compute_sha256(actual_bytes)
                if actual_sha.lower() != expected_sha.lower():
                    errors.append(
                        f"Checksum mismatch for '{rel_id}': expected SHA-256 {expected_sha}, got {actual_sha}"
                    )
            except Exception as e:
                errors.append(f"Failed to read and verify '{rel_id}': {e}")

    return len(errors) == 0, errors


def verify_ro_crate(crate_path: Path) -> Tuple[bool, List[str]]:
    """
    Verifies the structural and cryptographic integrity of an RO-Crate archive (.zip)
    or directory against its ro-crate-metadata.json manifest.
    """
    if not crate_path.exists():
        return False, [f"RO-Crate path does not exist: {crate_path}"]

    if crate_path.is_file() and (crate_path.suffix.lower() == ".zip" or ".crate" in crate_path.name):
        try:
            with zipfile.ZipFile(crate_path, "r") as zf:
                if "ro-crate-metadata.json" not in zf.namelist():
                    return False, ["Missing root 'ro-crate-metadata.json' in crate ZIP archive"]
                raw_bytes = zf.read("ro-crate-metadata.json")
                manifest_data = json.loads(raw_bytes.decode("utf-8"))

                file_reader = lambda rel: zf.read(rel)
                file_exists = lambda rel: rel in zf.namelist()
                return _verify_manifest_and_files(manifest_data, file_reader, file_exists)
        except Exception as e:
            return False, [f"Failed to open or parse crate ZIP archive: {e}"]
    elif crate_path.is_dir():
        manifest_file = crate_path / "ro-crate-metadata.json"
        if not manifest_file.is_file():
            return False, ["Missing root 'ro-crate-metadata.json' in crate directory"]
        try:
            manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
            file_reader = lambda rel: (crate_path / rel).read_bytes()
            file_exists = lambda rel: (crate_path / rel).is_file()
            return _verify_manifest_and_files(manifest_data, file_reader, file_exists)
        except Exception as e:
            return False, [f"Failed to read or parse ro-crate-metadata.json: {e}"]
    else:
        return False, [f"Invalid crate path format: {crate_path}"]
