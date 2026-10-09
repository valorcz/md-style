"""
tests/test_pygments_highlighting.py
Unit tests for Pygments syntax highlighting, language aliases, and CSS bundling.
"""

from pathlib import Path
from core.parser import MarkdownParser
from core.bundler import AssetBundler
from core.themes import ThemeResolver

def test_pygments_token_spans_generated():
    parser = MarkdownParser()
    src = """
```python
def inspect_artifact(file_path: str) -> bool:
    return True
```
"""
    html_out, _, _ = parser.render(src)
    assert '<pre class="highlight-code" data-lang="python">' in html_out
    assert '<code class="language-python">' in html_out
    assert 'class="tok-k"' in html_out  # def / return
    assert 'class="tok-nf"' in html_out # inspect_artifact function name

def test_pygments_language_aliases():
    parser = MarkdownParser()
    src = """
```hex
00000000: 4d 5a 90 00 03 00 00 00 04 00 00 00 ff ff 00 00  MZ..............
```

```ps1
$Action = New-ScheduledTaskAction -Execute "cmd.exe"
```
"""
    html_out, _, _ = parser.render(src)
    assert '<pre class="highlight-code" data-lang="hex">' in html_out
    assert '<pre class="highlight-code" data-lang="ps1">' in html_out
    assert 'class="tok-' in html_out

def test_asset_bundler_injects_pygments_css(tmp_path):
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text("# Test\n```python\nprint(1)\n```", encoding="utf-8")

    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/dossier")

    bundler = AssetBundler(doc_path)
    html = bundler.assemble(
        html_fragment='<pre class="highlight-code"><code class="language-python"><span class="tok-nb">print</span>(1)</code></pre>',
        theme=theme
    )

    assert "Pygments Syntax Highlighting" in html
    assert ".highlight-code .tok-" in html
