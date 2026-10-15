import type { DocumentAnnotation } from './types';

/**
 * Generates a clean, detached, self-contained HTML bundle containing the latest annotations.
 * Strips all transient Svelte DOM runtime nodes and escapes JSON safely.
 */
export function exportUpdatedHtmlBundle(annotations: DocumentAnnotation[], docTitle: string): void {
  // 1. Clone detached documentElement
  const clone = document.documentElement.cloneNode(true) as HTMLElement;

  // 2. Remove all runtime Svelte UI roots & injected components
  clone.querySelectorAll('#md-style-viewer-root').forEach(el => el.remove());
  clone.querySelectorAll('.table-toolbar-container').forEach(el => el.remove());
  clone.querySelectorAll('.annotation-popover').forEach(el => el.remove());
  clone.querySelectorAll('.margin-gutter').forEach(el => el.remove());

  // 3. Unwrap all runtime highlight mark tags back to original text nodes
  clone.querySelectorAll('mark.md-annotation-mark').forEach(mark => {
    mark.replaceWith(...Array.from(mark.childNodes));
  });

  // 4. Reset modified body/html classes
  const body = clone.querySelector('body');
  if (body) {
    body.classList.remove('inspector-open', 'paged-view');
  }

  // 5. Update or inject clean #md-style-annotations script tag
  let annScript = clone.querySelector('#md-style-annotations');
  if (!annScript) {
    annScript = document.createElement('script');
    annScript.id = 'md-style-annotations';
    annScript.setAttribute('type', 'application/json');
    const firstScript = body?.querySelector('script');
    if (firstScript) {
      body?.insertBefore(annScript, firstScript);
    } else {
      body?.appendChild(annScript);
    }
  }

  // 6. Escape '<' to prevent script breakout XSS
  const safeJson = JSON.stringify({
    version: '1.0',
    updated_at: new Date().toISOString(),
    annotations
  }, null, 2).replace(/</g, '\\u003c');

  annScript.textContent = safeJson;

  // 7. Ensure empty viewer root is present for clean next mount
  if (!clone.querySelector('#md-style-viewer-root')) {
    const rootEl = document.createElement('div');
    rootEl.id = 'md-style-viewer-root';
    clone.appendChild(rootEl);
  }

  // 8. Trigger browser download
  const fullHtml = '<!DOCTYPE html>\n' + clone.outerHTML;
  const blob = new Blob([fullHtml], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeFilename = (docTitle || 'report').toLowerCase().replace(/[^a-z0-9_-]+/g, '-') + '-annotated.html';
  a.download = safeFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

/**
 * Maps annotations back into raw Markdown source using context-bounded CriticMarkup tokens.
 */
export function exportCriticMarkdown(rawMarkdown: string, annotations: DocumentAnnotation[], docTitle: string): void {
  if (!rawMarkdown) {
    console.warn('[Export] No source markdown available to annotate.');
    return;
  }

  let updatedMd = rawMarkdown;

  // Sort annotations in reverse order of text offset/quote length to avoid offset displacement
  const sorted = [...annotations].filter(a => !a.resolved).sort((a, b) => {
    return (b.range?.quote?.length || 0) - (a.range?.quote?.length || 0);
  });

  const unmapped: DocumentAnnotation[] = [];

  for (const ann of sorted) {
    const quote = ann.range?.quote?.trim();
    if (!quote) continue;

    // Sanitize comment to avoid premature CriticMarkup tag closure if user wrote <<
    const safeComment = (ann.text || '').replace(/<</g, '<\\<');
    const criticTag = `{==${quote}==}{>>[${ann.category.toUpperCase()}${ann.author ? ' | ' + ann.author : ''}]: ${safeComment}<<}`;

    // 1. Try context-bounded search first
    const prefix = ann.range?.prefixContext?.trim() || '';
    const suffix = ann.range?.suffixContext?.trim() || '';
    let mapped = false;

    if (prefix && suffix) {
      // Find candidate window
      const ctxPattern = escapeRegExp(prefix) + '[\\s\\S]{0,120}' + escapeRegExp(quote) + '[\\s\\S]{0,120}' + escapeRegExp(suffix);
      const re = new RegExp(ctxPattern, 'i');
      const match = updatedMd.match(re);
      if (match && match.index !== undefined) {
        // Offset search past prefix to avoid matching quote inside prefixContext
        const searchStart = match.index + (prefix ? prefix.length : 0);
        const quoteIdx = updatedMd.indexOf(quote, searchStart);
        if (quoteIdx !== -1) {
          updatedMd = updatedMd.slice(0, quoteIdx) + criticTag + updatedMd.slice(quoteIdx + quote.length);
          mapped = true;
        }
      }
    }

    // 2. Direct exact quote match if context match failed
    if (!mapped) {
      const idx = updatedMd.indexOf(quote);
      if (idx !== -1) {
        updatedMd = updatedMd.slice(0, idx) + criticTag + updatedMd.slice(idx + quote.length);
        mapped = true;
      }
    }

    if (!mapped) {
      unmapped.push(ann);
    }
  }

  // 3. Fallback: Append unmapped annotations in a Review Appendix section
  if (unmapped.length > 0) {
    updatedMd += '\n\n---\n\n## Review Feedback Appendix\n\n';
    for (const ann of unmapped) {
      updatedMd += `- **[${ann.category.toUpperCase()}]** On *"${ann.range.quote}"*: ${ann.text} (by ${ann.author})\n`;
    }
  }

  // Download .md file
  const blob = new Blob([updatedMd], { type: 'text/markdown;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  const safeFilename = (docTitle || 'report').toLowerCase().replace(/[^a-z0-9_-]+/g, '-') + '-reviewed.md';
  a.download = safeFilename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

function escapeRegExp(string: string): string {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}
