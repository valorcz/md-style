"""
core/kb/lifecycle.py
Knowledge Pack lifecycle manager: source hashing, entity provenance, and refresh orchestration.
"""

import re
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

        # On force refresh, clear non-overridden entities to rebuild cleanly and purge old/duplicate IDs
        if refresh_mode == "force":
            self.pack.entities = {
                eid: ent for eid, ent in self.pack.entities.items()
                if ent.provenance and ent.provenance.manual_override
            }

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

                is_hollow = (
                    existing_ent is not None
                    and (
                        (existing_ent.provenance and existing_ent.provenance.status == "unresolved")
                        or (not existing_ent.details and not existing_ent.metrics and not existing_ent.attributes)
                    )
                )

                if refresh_mode == "force":
                    tokens_to_resolve.add(c)
                elif not has_existing or c not in self.pack.entities:
                    tokens_to_resolve.add(c)
                elif is_hollow:
                    # Auto-refresh hollow entity stubs or previously unresolved tokens
                    tokens_to_resolve.add(c)
                elif refresh_mode == "incremental":
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
                        existing = self.pack.entities.get(ent.id)
                        if existing:
                            # Merge aliases into existing canonical entity
                            for a in [token, *ent.aliases]:
                                if a and a not in existing.aliases:
                                    existing.aliases.append(a)
                            # If existing was unresolved and new is resolved, upgrade it
                            if existing.provenance and existing.provenance.status == "unresolved" and ent.provenance and ent.provenance.status == "resolved":
                                self.pack.entities[ent.id] = ent
                        else:
                            if token not in ent.aliases:
                                ent.aliases.append(token)
                            self.pack.entities[ent.id] = ent
                        entities_resolved += 1
                    break

        # 3. Transitive Graph Closure (Bounded Expansion: Max Depth = 1)
        # Discovers connected entities (e.g. CVE from GHSA, MITRE from Event, parent techniques)
        # and resolves them into first-class entities with bidirectional relationship linking.
        transitive_resolved = 0
        MAX_ENTITIES_BUDGET = 100

        # Collect outgoing candidate targets from current entities
        expansion_queue: List[Tuple[str, str, str]] = []  # (target_token, source_entity_id, relation_type)
        for parent_id, parent_ent in list(self.pack.entities.items()):
            # A. GHSA associated CVE and CWEs
            if parent_ent.type == "ghsa":
                cve_target = parent_ent.attributes.get("CVE") or parent_ent.details.get("Associated CVE")
                if cve_target and cve_target.upper().startswith("CVE-"):
                    expansion_queue.append((cve_target.strip().upper(), parent_id, "corresponds_to"))
                for rel in parent_ent.relationships:
                    if rel.get("type") == "cve" and rel.get("target"):
                        expansion_queue.append((rel["target"].strip().upper(), parent_id, rel.get("relation", "corresponds_to")))

                # Extract CWEs from GHSA details
                cwe_raw = parent_ent.details.get("CWE Identifiers", "")
                for cwe_match in re.findall(r"\b(CWE-\d{1,5})\b", str(cwe_raw), re.I):
                    expansion_queue.append((cwe_match.strip().upper(), parent_id, "categorized_as"))

            # B. CVE associated CWEs
            elif parent_ent.type == "cve":
                cwes = parent_ent.classification.get("cwes", [])
                for cwe in cwes:
                    if isinstance(cwe, str) and cwe.upper().startswith("CWE-"):
                        expansion_queue.append((cwe.strip().upper(), parent_id, "categorized_as"))
                for rel in parent_ent.relationships:
                    if rel.get("type") == "cwe" and rel.get("target"):
                        expansion_queue.append((rel["target"].strip().upper(), parent_id, rel.get("relation", "categorized_as")))

            # C. Windows Event detected MITRE technique or logged_in EVTX channel
            elif parent_ent.type == "winevent":
                for rel in parent_ent.relationships:
                    t = rel.get("target")
                    if t and (rel.get("type") in ["mitre", "evtx"] or t.startswith("T") or t.endswith(".evtx")):
                        expansion_queue.append((t.strip(), parent_id, rel.get("relation", "related")))

            # D. MITRE sub-technique parent technique
            elif parent_ent.type == "mitre":
                for rel in parent_ent.relationships:
                    t = rel.get("target")
                    if t and rel.get("relation") == "subtechnique_of":
                        expansion_queue.append((t.strip(), parent_id, "subtechnique_of"))


        # Process expansion queue
        for target_token, source_id, rel_type in expansion_queue:
            if len(self.pack.entities) >= MAX_ENTITIES_BUDGET:
                break

            # If already resolved and not hollow, ensure bidirectional relationship exists
            existing_target = self.pack.entities.get(target_token)
            if existing_target and refresh_mode != "force":
                # Add back-reference if absent
                if not any(r.get("target") == source_id for r in existing_target.relationships):
                    source_ent = self.pack.entities.get(source_id)
                    s_type = source_ent.type if source_ent else "entity"
                    existing_target.relationships.append({
                        "target": source_id,
                        "type": s_type,
                        "relation": "referenced_by"
                    })
                continue

            # Attempt to resolve using active resolvers
            for resolver in active_resolvers:
                if resolver.can_handle(target_token):
                    ent = resolver.resolve(
                        target_token,
                        allow_online=allow_online,
                        force_refresh=(refresh_mode == "force")
                    )
                    if ent:
                        if existing_target:
                            # Preserve prior relationships
                            for er in existing_target.relationships:
                                if not any(r.get("target") == er.get("target") for r in ent.relationships):
                                    ent.relationships.append(er)
                        # Tag provenance as transitively discovered
                        ent.provenance = Provenance(
                            source=f"transitive:{source_id}",
                            fetched_at=datetime.now(timezone.utc).isoformat(),
                            status="resolved",
                            details={"discovered_via": source_id, "relation": rel_type}
                        )
                        # Establish bidirectional relationship link back to parent
                        source_ent = self.pack.entities.get(source_id)
                        s_type = source_ent.type if source_ent else "entity"
                        if not any(r.get("target") == source_id for r in ent.relationships):
                            ent.relationships.append({
                                "target": source_id,
                                "type": s_type,
                                "relation": "referenced_by"
                            })

                        self.pack.entities[ent.id] = ent
                        transitive_resolved += 1
                        Diagnostics.debug_log(f"Transitive closure resolved {ent.id} via {source_id}")
                    break

        if entities_resolved > 0 or transitive_resolved > 0 or sources_updated or not has_existing:
            self.save_pack()

        return self.pack
