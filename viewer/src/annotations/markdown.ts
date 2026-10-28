import { marked } from 'marked';
import DOMPurify from 'dompurify';

// Configure marked with GFM and line breaks
marked.setOptions({
  gfm: true,
  breaks: true
});

// Configure DOMPurify hook to prevent reverse tabnabbing on links
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank');
    node.setAttribute('rel', 'noopener noreferrer');
  }
});

const ALLOWED_TAGS = [
  'b', 'i', 'em', 'strong', 'a', 'code', 'pre', 'p', 'ul', 'ol', 'li',
  'blockquote', 'span', 'del', 'hr', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
];

const ALLOWED_ATTR = ['href', 'target', 'rel', 'class', 'title'];

/**
 * Safely compiles raw user Markdown into sanitized HTML.
 */
export function renderAnnotationMarkdown(rawMarkdown: string): string {
  if (!rawMarkdown) return '';
  try {
    const rawHtml = marked.parse(rawMarkdown) as string;
    return DOMPurify.sanitize(rawHtml, {
      ALLOWED_TAGS,
      ALLOWED_ATTR,
      ALLOW_UNKNOWN_PROTOCOLS: false
    });
  } catch (err) {
    console.warn('[Markdown] Failed to parse annotation markdown:', err);
    return DOMPurify.sanitize(rawMarkdown);
  }
}
