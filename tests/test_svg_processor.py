"""
tests/test_svg_processor.py
Unit tests verifying pure-Python SVG sanitization, ID namespacing,
CSS scoping, and viewBox normalization.
"""

from core.svg.processor import SVGProcessor


def test_svg_sanitization_removes_scripts_and_handlers():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
        <script>alert('xss')</script>
        <rect width="50" height="50" onclick="evil()" onload="leak()"/>
        <a href="javascript:alert(1)"><circle r="10"/></a>
    </svg>
    """
    proc = SVGProcessor(allow_online=True)
    out, ok = proc.process(svg, prefix="pfx", scope_id="fig_test")
    assert ok is True
    assert "<script" not in out
    assert "alert('xss')" not in out
    assert "onclick" not in out
    assert "onload" not in out
    assert "javascript:" not in out
    assert "<rect" in out


def test_svg_id_namespacing():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <defs>
            <clipPath id="clip0"><rect width="10" height="10"/></clipPath>
            <linearGradient id="grad1"><stop offset="0%"/></linearGradient>
        </defs>
        <path clip-path="url(#clip0)" fill="url(#grad1)"/>
        <use href="#clip0"/>
    </svg>
    """
    proc = SVGProcessor(allow_online=True)
    out, ok = proc.process(svg, prefix="svg_abc", scope_id="fig_test")
    assert ok is True
    assert 'id="svg_abc_clip0"' in out
    assert 'id="svg_abc_grad1"' in out
    assert 'url(#svg_abc_clip0)' in out
    assert 'url(#svg_abc_grad1)' in out
    assert 'href="#svg_abc_clip0"' in out


def test_svg_css_selector_scoping():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">
        <defs>
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
                text { fill: #0f172a; font-family: 'Inter', sans-serif; }
                .heading, .title { font-size: 16px; font-weight: 600; }
                rect.card { stroke: #e2e8f0; }
            </style>
        </defs>
        <rect class="card" width="100" height="50"/>
        <text class="heading">Sample</text>
    </svg>
    """
    proc = SVGProcessor(allow_online=True)
    out, ok = proc.process(svg, prefix="pfx", scope_id="fig_pyr")
    assert ok is True
    # @import must be preserved
    assert "@import url('https://fonts.googleapis.com/css2?family=Inter" in out
    # Selectors must be scoped to #fig_pyr
    assert "#fig_pyr text" in out
    assert "#fig_pyr .heading" in out
    assert "#fig_pyr .title" in out
    assert "#fig_pyr rect.card" in out


def test_svg_viewbox_synthesis():
    svg = '<svg xmlns="http://www.w3.org/2000/svg" width="800px" height="400px"><rect width="800" height="400"/></svg>'
    proc = SVGProcessor(allow_online=True)
    out, ok = proc.process(svg, prefix="pfx", scope_id="fig_1")
    assert ok is True
    assert 'viewBox="0 0 800 400"' in out
    assert 'width="100%"' in out
    assert 'preserveAspectRatio="xMidYMid meet"' in out


def test_svg_air_gap_strips_wan_links():
    svg = """
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
        <image href="https://example.com/external.png" width="50" height="50"/>
    </svg>
    """
    proc = SVGProcessor(allow_online=False)
    out, ok = proc.process(svg, prefix="pfx", scope_id="fig_1")
    assert ok is True
    assert "https://example.com/external.png" not in out
