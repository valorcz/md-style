"""
core/kb/lifecycle.py
Knowledge Pack lifecycle manager: source hashing, entity provenance, and refresh orchestration.
"""

import hashlib
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Set
from datetime import datetime, timezone

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

from core.kb.models import KnowledgePack, Entity, Provenance
from core.kb.loaders import get_loader
from core.kb.resolvers import get_default_resolvers, RESOLVER_REGISTRY
from core.diagnostics import Diagnostics

class KnowledgeLifecycleManager:
    """Orchestrates ingestion, token resolution, caching, and refresh for Knowledge Packs."""

    def __init__(self, doc_path: Path, catalog=None):
        self.doc_path = doc_path
        self.kb_json_path = doc_path.with_suffix(".kb.json")
        self.kb_yaml_path = doc_path.with_suffix(".kb.yaml")
        self.pack: KnowledgePack = KnowledgePack(document_id=doc_path.stem)
        self.resolvers = get_default_resolvers(catalog=catalog)

    @staticmethod
    def compute_file_hash(path: Path) -> Optional[str]:
        if not path.exists():
            return None
        h = hashlib.sha256()
        with open(path, "rb") as f:
            while chunk := f.read(65536):
                h.update(chunk)
        return f"sha256:{h.hexdigest()[:16]}"

    def load_existing_pack(self) -> bool:
        """Loads doc.kb.json if it exists."""
        if self.kb_json_path.exists():
            try:
                with open(self.kb_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.pack = KnowledgePack.from_dict(data)
                return True
            except Exception as e:
                Diagnostics.warn(f"Failed to read existing KB pack {self.kb_json_path}: {e}")
        return False

    def save_pack(self):
        """Saves current knowledge pack to doc.kb.json."""
        self.pack.generated_at = datetime.now(timezone.utc).isoformat()
        try:
            with open(self.kb_json_path, "w", encoding="utf-8") as f:
                json.dump(self.pack.to_dict(), f, indent=2, ensure_ascii=False)
            Diagnostics.debug_log(f"Saved Knowledge Pack to {self.kb_json_path}")
        except Exception as e:
            Diagnostics.warn(f"Failed to save Knowledge Pack: {e}")

    def discover_source_configs(self, frontmatter: Optional[Dict[str, Any]] = None) -> Tuple[List[Dict[str, Any]], List[str]]:
        """Discovers declared data sources and active resolver names."""
        sources: List[Dict[str, Any]] = []
        resolvers_filter: List[str] = []

        # 1. From sidecar doc.kb.yaml
        if self.kb_yaml_path.exists() and HAS_YAML:
            try:
                with open(self.kb_yaml_path, "r", encoding="utf-8") as f:
                    yaml_data = yaml.safe_load(f)
                if isinstance(yaml_data, dict):
                    kb_block = yaml_data.get("knowledge", yaml_data)
                    if isinstance(kb_block.get("sources"), list):
                        sources.extend(kb_block["sources"])
                    if isinstance(kb_block.get("resolvers"), list):
                        resolvers_filter.extend(kb_block["resolvers"])
            except Exception as e:
                Diagnostics.warn(f"Error reading sidecar {self.kb_yaml_path}: {e}")

        # 2. From frontmatter
        if frontmatter and isinstance(frontmatter, dict):
            kb_block = frontmatter.get("knowledge")
            if isinstance(kb_block, dict):
                if isinstance(kb_block.get("sources"), list):
                    sources.extend(kb_block["sources"])
                if isinstance(kb_block.get("resolvers"), list):
                    resolvers_filter.extend(kb_block["resolvers"])

        return sources, resolvers_filter

    def sync(
        self,
        raw_text: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        refresh_mode: Optional[str] = None,
        allow_online: bool = True
    ) -> KnowledgePack:
        """
        Main synchronization method.
        refresh_mode: None (air-gapped/cache), "incremental", "sources", "force"
        """
        has_existing = self.load_existing_pack()
        sources_cfg, resolvers_filter = self.discover_source_configs(frontmatter)

        # Filter active resolvers if specified
        active_resolvers = self.resolvers
        if resolvers_filter:
            active_resolvers = [r for r in self.resolvers if r.name in resolvers_filter]

        # 1. Ingest local structured sources (Excel, CSV, JSON)
        sources_updated = False
        new_digests: Dict[str, str] = {}

        for src_entry in sources_cfg:
            rel_path = src_entry.get("path")
            if not rel_path:
                continue

            src_path = (self.doc_path.parent / rel_path).resolve() if not Path(rel_path).is_absolute() else Path(rel_path)
            fhash = self.compute_file_hash(src_path)
            if not fhash:
                continue

            new_digests[src_entry.get("path")] = fhash
            old_hash = self.pack.sources_digest.get(src_entry.get("path"))

            # Determine if this source needs to be reloaded
            should_reload = (
                not has_existing
                or refresh_mode in ["sources", "force"]
                or (refresh_mode == "incremental" and old_hash != fhash)
                or (old_hash != fhash and not has_existing)
            )

            if should_reload:
                loader_type = src_entry.get("type", "json")
                try:
                    loader = get_loader(loader_type)
                    loaded_entities = loader.load(src_path, src_entry)
                    for ent in loaded_entities:
                        # Check manual override preservation
                        existing_ent = self.pack.entities.get(ent.id)
                        if existing_ent and existing_ent.provenance and existing_ent.provenance.manual_override:
                            continue
                        self.pack.entities[ent.id] = ent
                        sources_updated = True
                except Exception as e:
                    Diagnostics.warn(f"Failed loading source {src_path}: {e}")

        self.pack.sources_digest = new_digests

        # If refresh_mode == 'sources', we stop here and do not query online APIs
        if refresh_mode == "sources":
            if sources_updated or not has_existing:
                self.save_pack()
            return self.pack

        # 2. Extract and resolve candidate tokens from document text
        tokens_to_resolve: Set[str] = set()

        for resolver in active_resolvers:
            candidates = resolver.extract_candidates(raw_text)
            for c in candidates:
                existing_ent = self.pack.entities.get(c)
                # If entity already exists and is overridden, skip
                if existing_ent and existing_ent.provenance and existing_ent.provenance.manual_override:
                    continue

                if refresh_mode == "force":
                    tokens_to_resolve.add(c)
                elif not has_existing or c not in self.pack.entities:
                    tokens_to_resolve.add(c)
                elif refresh_mode == "incremental":
                    # If unresolved in previous run, try again
                    if existing_ent and existing_ent.provenance and existing_ent.provenance.status == "unresolved":
                        tokens_to_resolve.add(c)

        # Resolve tokens
        entities_resolved = 0
        for token in tokens_to_resolve:
            for resolver in active_resolvers:
                if resolver.can_handle(token):
                    ent = resolver.resolve(
                        token,
                        allow_online=allow_online,
                        force_refresh=(refresh_mode == "force")
                    )
                    if ent:
                        self.pack.entities[ent.id] = ent
                        entities_resolved += 1
                    break

        if entities_resolved > 0 or sources_updated or not has_existing:
            self.save_pack()

        return self.pack
