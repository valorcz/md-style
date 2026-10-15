"""
core/kb/resolvers/iban_resolver.py
Czech Bank Account & IBAN resolver with bank clearing code catalog and
Czech Banking Association (ČBA) SPAYD QR Platba generator.
"""

import re
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance, WidgetDescriptor
from core.i18n import I18nCatalog

# Domestic format: optional prefix (up to 6 digits) - account (2 to 10 digits) / bank code (4 digits)
DOMESTIC_REGEX = re.compile(r"(?:\b(\d{1,6})-)?(\d{2,10})/(\d{4})\b")
# Czech IBAN: CZ + 22 digits
IBAN_REGEX = re.compile(r"\b(CZ\d{22})\b", re.IGNORECASE)

BANK_CODES: Dict[str, Dict[str, str]] = {
    "0100": {"name": "Komerční banka, a.s.", "bic": "KOMBCZPP"},
    "0300": {"name": "Československá obchodní banka, a.s. (ČSOB)", "bic": "CEKOCZPP"},
    "0600": {"name": "MONETA Money Bank, a.s.", "bic": "AGBACZPP"},
    "0800": {"name": "Česká spořitelna, a.s.", "bic": "GIGACZPP"},
    "2010": {"name": "Fio banka, a.s.", "bic": "FIOBCZPP"},
    "2070": {"name": "Banka CREDITAS a.s.", "bic": "CREDCZPP"},
    "2600": {"name": "Citibank Europe plc", "bic": "CITICZPX"},
    "2700": {"name": "UniCredit Bank Czech Republic and Slovakia, a.s.", "bic": "BACXCZPP"},
    "3030": {"name": "Air Bank a.s.", "bic": "AIRACZPP"},
    "5500": {"name": "Raiffeisenbank a.s.", "bic": "RZBCCZPP"},
    "6210": {"name": "mBank S.A.", "bic": "BREXCZPP"},
    "8040": {"name": "Oberbank AG", "bic": "OBKLCZ2X"},
}


def czech_account_to_iban(prefix: str, account: str, bank_code: str) -> str:
    """Converts Czech domestic account number to official 24-character IBAN."""
    p_str = (prefix or "").zfill(6)
    a_str = account.zfill(10)
    b_str = bank_code.zfill(4)
    bban = f"{b_str}{p_str}{a_str}"

    # Calculate check digits: BBAN + "CZ00" -> C=12, Z=35
    rearranged = f"{bban}123500"
    num = int(rearranged)
    check_digits = 98 - (num % 97)
    return f"CZ{check_digits:02d}{bban}"


def parse_czech_iban(iban: str) -> Tuple[str, str, str]:
    """Extracts (prefix, account, bank_code) from a Czech IBAN."""
    clean = iban.upper().replace(" ", "")
    if len(clean) != 24 or not clean.startswith("CZ"):
        return ("", "", "")
    bank_code = clean[4:8]
    prefix = clean[8:14].lstrip("0")
    account = clean[14:24].lstrip("0")
    return (prefix, account, bank_code)


def generate_spayd(iban: str, amount: Optional[float] = None, vs: Optional[str] = None, msg: Optional[str] = None) -> str:
    """
    Generates standard Czech Banking Association (ČBA) SPAYD QR Platba string:
    SPD*1.0*ACC:CZ...*AM:...*CC:CZK*X-VS:...*MSG:...
    """
    parts = ["SPD*1.0", f"ACC:{iban}"]
    if amount and amount > 0:
        parts.append(f"AM:{amount:.2f}")
        parts.append("CC:CZK")
    if vs:
        parts.append(f"X-VS:{vs}")
    if msg:
        clean_msg = re.sub(r"[^\w\s.,-]", "", msg)[:60]
        parts.append(f"MSG:{clean_msg}")
    return "*".join(parts)


class IbanResolver(BaseResolver):
    name = "iban"

    def __init__(self, catalog: Optional[I18nCatalog] = None):
        self.catalog = catalog or I18nCatalog("cs")

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        m_dom = DOMESTIC_REGEX.search(t)
        if m_dom:
            bank_code = m_dom.group(3)
            return bank_code in BANK_CODES
        m_iban = IBAN_REGEX.search(t)
        if m_iban:
            return True
        return False

    def extract_candidates(self, text: str) -> List[str]:
        candidates: List[str] = []
        for m in DOMESTIC_REGEX.finditer(text):
            bank_code = m.group(3)
            if bank_code in BANK_CODES:
                start = m.start()
                pre = text[max(0, start - 10):start].lower()
                if not re.search(r"(?:č\.|číslo|zák\.|sb\.)\s*$", pre):
                    candidates.append(m.group(0))
        for m in IBAN_REGEX.finditer(text):
            candidates.append(m.group(0))
        return list(set(candidates))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        t = token.strip()
        prefix = ""
        account = ""
        bank_code = ""
        iban = ""

        m_dom = DOMESTIC_REGEX.search(t)
        m_iban = IBAN_REGEX.search(t)

        if m_dom:
            bank_code = m_dom.group(3)
            if bank_code not in BANK_CODES:
                return None
            prefix = m_dom.group(1) or ""
            account = m_dom.group(2)
            iban = czech_account_to_iban(prefix, account, bank_code)
        elif m_iban:
            iban = m_iban.group(1).upper()
            prefix, account, bank_code = parse_czech_iban(iban)
            if bank_code not in BANK_CODES:
                return None
        else:
            return None

        bank_info = BANK_CODES.get(bank_code, {"name": f"Banka s kódem {bank_code}", "bic": "UNKNOWN"})
        bank_name = bank_info["name"]
        bic = bank_info["bic"]

        domestic_display = f"{prefix + '-' if prefix else ''}{account}/{bank_code}"
        spayd_string = generate_spayd(iban=iban, msg="Platba SVJ")

        prov = Provenance(
            source="cnb:czech-national-bank",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved",
            manual_override=False
        )

        widgets: List[WidgetDescriptor] = [
            WidgetDescriptor(
                widget_type="qr_platba",
                title="Czech QR Platba (Standard ČBA)",
                tone="success",
                data={
                    "account": domestic_display,
                    "iban": iban,
                    "bank_code": bank_code,
                    "bank_name": bank_name,
                    "bic": bic,
                    "spayd": spayd_string
                }
            ),
            WidgetDescriptor(
                widget_type="attributes_table",
                title="Platební spojení",
                data={
                    "Číslo účtu": domestic_display,
                    "Mezinárodní formát IBAN": iban,
                    "SWIFT / BIC": bic,
                    "Finanční instituce": bank_name,
                    "Kód banky": bank_code,
                    "Měna": "CZK (Česká koruna)"
                }
            )
        ]

        return Entity(
            id=f"iban-{iban}",
            domain="finance",
            type="iban",
            label=domestic_display,
            title=f"Účet {domestic_display} – {bank_name}",
            severity="INFO",
            badge="BANKOVNÍ SPOJENÍ & QR PLATBA",
            summary=f"Tuzemský bankovní účet {domestic_display} vedený u {bank_name} (IBAN: {iban}, BIC: {bic}).",
            attributes={
                "Číslo účtu": domestic_display,
                "IBAN": iban,
                "Banka": bank_name,
                "SWIFT / BIC": bic
            },
            references=[],
            provenance=prov,
            widgets=widgets,
            aliases=[
                domestic_display,
                iban,
                f"účet {domestic_display}",
                f"č.ú. {domestic_display}"
            ]
        )
