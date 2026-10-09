"""
core/kb/resolvers/statute_resolver.py
Legal and statutory provisions resolver for Czech legal codes (NOZ, ZOK) and GDPR.
"""

import re
from typing import Optional, List
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.i18n import I18nCatalog

STATUTE_REGEX = re.compile(r"(?:§\s*(\d+[a-z]?)|čl\.\s*(\d+))\s*(?:odst\.\s*(\d+))?", re.IGNORECASE)

KNOWN_STATUTES = {
    "1205": {
        "title": "§ 1205 NOZ - Orgány společenství vlastníků jednotek",
        "act": "Zákon č. 89/2012 Sb., občanský zákoník",
        "summary": "Nejvyšším orgánem společenství vlastníků je shromáždění. Statutárním orgánem je výbor, ledaže stanovy určí, že je statutárním orgánem předseda společenství vlastníků.",
        "url": "https://www.zakonyprolidi.cz/cs/2012-89#p1205"
    },
    "1186": {
        "title": "§ 1186 NOZ - Převod vlastnického práva k jednotce",
        "act": "Zákon č. 89/2012 Sb., občanský zákoník",
        "summary": "Při převodu vlastnického práva k jednotce nevzniká osobě odpovědné za správu domu povinnost příspěvky na správu domu vypořádat. Převodce předloží nabyvateli potvrzení o dluzích.",
        "url": "https://www.zakonyprolidi.cz/cs/2012-89#p1186"
    },
    "1206": {
        "title": "§ 1206 NOZ - Usnášeníschopnost shromáždění",
        "act": "Zákon č. 89/2012 Sb., občanský zákoník",
        "summary": "Shromáždění je způsobilé usnášet se za přítomnosti vlastníků jednotek, kteří mají většinu všech hlasů. K přijetí rozhodnutí se vyžaduje většina hlasů přítomných vlastníků jednotek, ledaže stanovy vyžadují vyšší počet hlasů.",
        "url": "https://www.zakonyprolidi.cz/cs/2012-89#p1206"
    },
    "1207": {
        "title": "§ 1207 NOZ - Svolání shromáždění vlastníků",
        "act": "Zákon č. 89/2012 Sb., občanský zákoník",
        "summary": "Statutární orgán svolá shromáždění k zasedání tak, aby se konalo nejméně jedenkrát do roka.",
        "url": "https://www.zakonyprolidi.cz/cs/2012-89#p1207"
    }
}

class StatuteResolver(BaseResolver):
    name = "statute"

    def __init__(self, catalog: Optional[I18nCatalog] = None):
        self.catalog = catalog or I18nCatalog("cs")

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        return bool(STATUTE_REGEX.search(t))

    def extract_candidates(self, text: str) -> List[str]:
        return [m.group(0) for m in STATUTE_REGEX.finditer(text)]

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        m = STATUTE_REGEX.search(token.strip())
        if not m:
            return None

        sec_num = m.group(1) or m.group(2)
        info = KNOWN_STATUTES.get(sec_num)
        if not info:
            info = {
                "title": f"Ustanovení § {sec_num}",
                "act": "Zákonné ustanovení",
                "summary": f"Odkaz na paragraf {sec_num}.",
                "url": ""
            }

        prov = Provenance(
            source="statute:czech-legal-code",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved",
            manual_override=False
        )

        refs = [{"title": info["act"], "url": info["url"]}] if info.get("url") else []

        return Entity(
            id=f"statute-{sec_num}",
            domain="legal",
            type="statute",
            label=f"§ {sec_num}",
            title=info["title"],
            severity="INFO",
            badge=self.catalog.t("badges.statute", default="ZÁKONNÉ USTANOVENÍ"),
            summary=info["summary"],
            attributes={
                "Předpis": info["act"],
                "Paragraf": f"§ {sec_num}"
            },
            references=refs,
            provenance=prov,
            aliases=[f"§ {sec_num}", f"§{sec_num}"]
        )
