"""
tests/test_svj_framework.py
Unit and integration test suite for the Public Administration & SVJ (Condominium Owners' Association)
framework: Czech Statutes (NOZ, ZOK, Zákon o službách, NV 366/2013, GDPR), Business Entity (IČO & ARES),
Bank Account & Czech QR Platba (SPAYD), and document review annotations.
"""

from pathlib import Path
import pytest

from core.kb.resolvers.statute_resolver import StatuteResolver
from core.kb.resolvers.ico_resolver import IcoResolver, verify_ico_checksum
from core.kb.resolvers.iban_resolver import IbanResolver, czech_account_to_iban, generate_spayd
from core.engine import ReportEngine, PipelineConfig


def test_statute_resolver_svj_provisions():
    resolver = StatuteResolver()

    # 1. NOZ § 1206 (Quorum)
    assert resolver.can_handle("§ 1206 NOZ")
    ent_1206 = resolver.resolve("§ 1206 NOZ")
    assert ent_1206 is not None
    assert ent_1206.id == "statute-1206"
    assert "Usnášeníschopnost" in ent_1206.title
    assert "zakonyprolidi.cz" in ent_1206.references[0]["url"]
    assert any(w.widget_type == "tactical_box" for w in ent_1206.widgets)

    # 2. NOZ § 1180 (Repair fund)
    ent_1180 = resolver.resolve("§ 1180")
    assert ent_1180 is not None
    assert "Fond oprav" in ent_1180.title

    # 3. Zákon o službách § 8a (Měsíční odečty)
    assert resolver.can_handle("§ 8a zákona o službách č. 67/2013 Sb.")
    ent_8a = resolver.resolve("§ 8a zákona o službách č. 67/2013 Sb.")
    assert ent_8a is not None
    assert ent_8a.id == "statute-67-8a"
    assert "dálkově odečítaná měřidla" in ent_8a.summary

    # 4. NV č. 366/2013 Sb. § 6 (Společné části domu)
    ent_nv6 = resolver.resolve("§ 6 nařízení vlády č. 366/2013 Sb.")
    assert ent_nv6 is not None
    assert ent_nv6.id == "statute-nv366-6"
    assert "Společnými částmi domu jsou rozvody tepla" in ent_nv6.summary

    # 5. GDPR čl. 6 (Kamerové systémy / Oprávněný zájem)
    ent_gdpr = resolver.resolve("čl. 6 GDPR")
    assert ent_gdpr is not None
    assert ent_gdpr.id == "statute-gdpr-6"
    assert "Oprávněný zájem" in ent_gdpr.title


def test_ico_resolver_checksum_and_resolution(tmp_path):
    # Test modulo-11 checksums
    assert verify_ico_checksum("00006947") is True  # Ministry of Finance
    assert verify_ico_checksum("26168685") is True  # Seznam.cz
    assert verify_ico_checksum("12345678") is False # Invalid check digit

    cache_file = tmp_path / "ares_test.json"
    resolver = IcoResolver(cache_file=cache_file)

    # 1. Known SVJ entity
    assert resolver.can_handle("IČO: 76543210")
    ent_svj = resolver.resolve("IČO: 76543210", allow_online=False)
    assert ent_svj is not None
    assert ent_svj.id == "ico-76543210"
    assert "Společenství vlastníků jednotek" in ent_svj.title
    assert "Jabloňová 1420/24" in ent_svj.attributes["Sídlo"]
    assert any("ares.gov.cz" in r["url"] for r in ent_svj.references)
    assert any("justice.cz" in r["url"] for r in ent_svj.references)

    # 2. Known ministry entity with valid modulo-11
    ent_mf = resolver.resolve("00006947", allow_online=False)
    assert ent_mf is not None
    assert "Ministerstvo financí" in ent_mf.title

    # 3. Unprefixed invalid number should be rejected
    assert resolver.can_handle("12345678") is False
    assert resolver.resolve("12345678", allow_online=False) is None


def test_iban_resolver_and_spayd():
    resolver = IbanResolver()

    # Domestic Czech format
    token = "1420-76543210/0100"
    assert resolver.can_handle(token)
    ent = resolver.resolve(token)
    assert ent is not None
    assert ent.domain == "finance"
    assert ent.type == "iban"
    assert "Komerční banka" in ent.title

    # Verify IBAN conversion
    expected_iban = czech_account_to_iban(prefix="1420", account="76543210", bank_code="0100")
    assert ent.attributes["IBAN"] == expected_iban
    assert expected_iban.startswith("CZ")
    assert len(expected_iban) == 24

    # Verify SPAYD widget
    qr_widget = next(w for w in ent.widgets if w.widget_type == "qr_platba")
    assert qr_widget is not None
    assert qr_widget.data["account"] == token
    assert qr_widget.data["iban"] == expected_iban
    assert "SPD*1.0" in qr_widget.data["spayd"]
    assert f"ACC:{expected_iban}" in qr_widget.data["spayd"]


def test_svj_document_compilation_e2e(tmp_path):
    svj_doc = Path("examples/pozvánka-shromáždění-svj.md")
    assert svj_doc.is_file()

    out_html = tmp_path / "svj_output.html"
    cfg = PipelineConfig(
        input_file=svj_doc,
        output_file=out_html,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    result = engine.run()

    assert result.is_file()
    html = result.read_text(encoding="utf-8")

    # 1. Verify theme applied
    assert "theme-svj-invitation" in html

    # 2. Verify Knowledge Pack entities embedded in HTML
    assert '<script id="md-style-kb-data"' in html
    assert "ico-76543210" in html
    assert "statute-1206" in html
    assert "statute-1180" in html
    assert "iban-CZ4401000014200076543210" in html

    # 3. Verify inline inspectable spans generated in HTML main content
    assert 'data-token="ico-76543210"' in html
    assert 'data-token="statute-1206"' in html
    assert 'data-token="iban-CZ4401000014200076543210"' in html

    # 4. Verify embedded annotations manifest
    assert '<script id="md-style-annotations"' in html
    assert "ann-svj-01" in html
    assert "K. Svoboda (Byt č. 3)" in html
    assert "Ing. Marie Černá" in html


def test_statute_resolver_dynamic_caching_and_offline(tmp_path):
    cache_file = tmp_path / "statutes_cache.json"
    custom_db = tmp_path / "custom_statutes.json"
    custom_db.write_text('{"9999": {"title": "§ 9999 Custom Law", "act": "Zákon č. 99/9999 Sb.", "summary": "Custom test summary", "url": "https://example.com"}}', encoding="utf-8")

    resolver = StatuteResolver(db_path=custom_db, cache_path=cache_file)

    # 1. Verify custom DB loaded
    ent_custom = resolver.resolve("§ 9999", allow_online=False)
    assert ent_custom is not None
    assert ent_custom.id == "statute-9999"
    assert ent_custom.title == "§ 9999 Custom Law"

    # 2. Unknown statute with allow_online=False -> offline fallback without network
    ent_offline = resolver.resolve("§ 1179", allow_online=False)
    assert ent_offline is not None
    assert ent_offline.id == "statute-1179"
    assert "Odkaz na zákonné ustanovení" in ent_offline.summary
    assert ent_offline.provenance.source == "statute:czech-legal-code"

    # 3. Dynamic online fetch for ZoKB / cybersecurity law (§ 5 zákona č. 181/2014 Sb.)
    # We can mock or test real fetch
    ent_zokb = resolver.resolve("§ 5 zákona č. 181/2014 Sb.", allow_online=True)
    assert ent_zokb is not None
    assert "statute-181-2014-5" in ent_zokb.id or "statute-5" in ent_zokb.id
    assert "181/2014" in ent_zokb.attributes["Předpis"]
    # Check that it cached to disk
    assert cache_file.exists()
    cached_content = cache_file.read_text(encoding="utf-8")
    assert "181" in cached_content or "organizační opatření" in cached_content or "zakonyprolidi" in cached_content

