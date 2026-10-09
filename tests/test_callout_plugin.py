"""
tests/test_callout_plugin.py
Unit tests for unified callouts plugin (GitHub alerts and container callouts).
"""

from core.parser import MarkdownParser
from core.i18n import I18nCatalog

def test_github_alert_custom_title():
    p = MarkdownParser()
    src = """
> [!CRITICAL] Immediate Domain Quarantine
> Active C2 beaconing observed.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-critical critical"' in html_out
    assert 'Immediate Domain Quarantine' in html_out
    assert '<svg class="callout-icon"' in html_out

def test_container_callout():
    p = MarkdownParser()
    src = """
::: warning Suspicious Memory Dump
Found unlinked executable memory segment.
:::
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-warning warning"' in html_out
    assert 'Suspicious Memory Dump' in html_out

def test_dfir_alert_types():
    p = MarkdownParser()
    src = """
> [!EVIDENCE] Hard Drive Bitstream
> SHA256 verified.

> [!FINDING] Lateral Movement
> SMB traversal confirmed.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-evidence evidence"' in html_out
    assert 'class="callout callout-finding finding"' in html_out
