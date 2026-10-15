"""
core/kb/models.py
Standardized Knowledge Pack entity, provenance, and bundle data models.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

@dataclass
class Provenance:
    source: str
    fetched_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "resolved"  # "resolved", "unresolved", "cached", "manual"
    manual_override: bool = False
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        if self.details is None:
            del d["details"]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Provenance":
        return cls(
            source=data.get("source", "unknown"),
            fetched_at=data.get("fetched_at", datetime.now(timezone.utc).isoformat()),
            status=data.get("status", "resolved"),
            manual_override=bool(data.get("manual_override", False)),
            details=data.get("details")
        )

@dataclass
class WidgetDescriptor:
    widget_type: str  # e.g. "gauge", "tactical_box", "rank_badge", "attributes_grid", "code_snippet"
    title: str = ""
    tone: str = "neutral"  # "threat", "defense", "telemetry", "info", "neutral"
    data: Dict[str, Any] = field(default_factory=dict)
    items: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WidgetDescriptor":
        return cls(
            widget_type=str(data.get("widget_type", "attributes_grid")),
            title=str(data.get("title", "")),
            tone=str(data.get("tone", "neutral")),
            data=dict(data.get("data", {})),
            items=list(data.get("items", []))
        )

DEFAULT_JSONLD_CONTEXT: Dict[str, Any] = {
    "@vocab": "https://schema.org/",
    "id": "@id",
    "type": "@type",
    "entities": "@graph",
    "cve": "https://cve.mitre.org/schema/",
    "statute": "https://schema.org/Legislation",
    "ico": "https://schema.org/Organization",
    "iban": "https://schema.org/BankOrCreditUnion",
    "provenance": "http://www.w3.org/ns/prov#wasDerivedFrom",
    "fetched_at": "http://www.w3.org/ns/prov#generatedAtTime",
    "relationships": "https://schema.org/mentions"
}


@dataclass
class Entity:
    id: str
    domain: str  # e.g. "cyber", "internal", "legal", "infrastructure"
    type: str    # e.g. "cve", "ghsa", "winevent", "evtx", "mitre", "statute", "asset", "hash"
    label: str
    title: str
    severity: str = "INFO"  # "CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"
    badge: str = ""
    summary: str = ""
    attributes: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    classification: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    relationships: List[Dict[str, str]] = field(default_factory=list)
    references: List[Dict[str, str]] = field(default_factory=list)
    provenance: Optional[Provenance] = None
    aliases: List[str] = field(default_factory=list)
    widgets: List[WidgetDescriptor] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        res = {
            "@type": self.type,
            "id": self.id,
            "domain": self.domain,
            "type": self.type,
            "label": self.label,
            "title": self.title,
            "severity": self.severity,
            "badge": self.badge,
            "summary": self.summary,
            "attributes": self.attributes,
            "metrics": self.metrics,
            "classification": self.classification,
            "details": self.details,
            "relationships": self.relationships,
            "references": self.references,
            "aliases": self.aliases,
            "widgets": [w.to_dict() if hasattr(w, "to_dict") else w for w in self.widgets],
        }
        if self.provenance:
            res["provenance"] = self.provenance.to_dict()
        return res

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Entity":
        prov_data = data.get("provenance")
        prov = Provenance.from_dict(prov_data) if prov_data else None
        return cls(
            id=str(data.get("id", "")),
            domain=str(data.get("domain", "general")),
            type=str(data.get("type", "entity")),
            label=str(data.get("label") or data.get("id", "")),
            title=str(data.get("title") or data.get("id", "")),
            severity=str(data.get("severity", "INFO")).upper(),
            badge=str(data.get("badge", "")),
            summary=str(data.get("summary", "")),
            attributes=dict(data.get("attributes", {})),
            metrics=dict(data.get("metrics", {})),
            classification=dict(data.get("classification", {})),
            details=dict(data.get("details", {})),
            relationships=list(data.get("relationships", [])),
            references=list(data.get("references", [])),
            provenance=prov,
            aliases=list(data.get("aliases", [])),
            widgets=[WidgetDescriptor.from_dict(w) if isinstance(w, dict) else w for w in data.get("widgets", [])]
        )

@dataclass
class KnowledgePack:
    version: str = "1.0"
    document_id: str = "default"
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sources_digest: Dict[str, str] = field(default_factory=dict)
    entities: Dict[str, Entity] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "@context": DEFAULT_JSONLD_CONTEXT,
            "@type": "Dataset",
            "version": self.version,
            "document_id": self.document_id,
            "generated_at": self.generated_at,
            "sources_digest": self.sources_digest,
            "entities": {k: v.to_dict() for k, v in self.entities.items()}
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "KnowledgePack":
        entities_raw = data.get("entities", {})
        entities = {}
        for k, v in entities_raw.items():
            if isinstance(v, dict):
                entities[k] = Entity.from_dict(v)
        return cls(
            version=str(data.get("version", "1.0")),
            document_id=str(data.get("document_id", "default")),
            generated_at=str(data.get("generated_at", "")),
            sources_digest=dict(data.get("sources_digest", {})),
            entities=entities
        )
