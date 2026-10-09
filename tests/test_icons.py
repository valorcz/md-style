"""
tests/test_icons.py
Unit tests for externalized IconService.
"""

from core.icons import IconService

def test_icon_service_loads_local_svg():
    svc = IconService()
    svg = svc.get_svg("info")

    assert "<svg" in svg
    assert 'class="callout-icon"' in svg
    assert 'viewBox="0 0 16 16"' in svg
    assert 'fill="currentColor"' in svg

def test_icon_service_custom_class():
    svc = IconService()
    svg = svc.get_svg("alert", extra_classes="custom-alert-icon")

    assert 'class="custom-alert-icon"' in svg
