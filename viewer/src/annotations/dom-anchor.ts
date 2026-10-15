import type { RangeSelector, DocumentAnnotation } from './types';

/**
 * Extracts a robust RangeSelector from a live DOM Range.
 */
export function serializeRange(range: Range): RangeSelector | null {
  const quote = range.toString();
  if (!quote.trim()) return null;

  // Find candidate block container within <main> or .report-content
  const root = document.querySelector('.report-content') || document.querySelector('main') || document.body;
  const commonAncestor = range.commonAncestorContainer;
  const blockEl = findClosestBlock(commonAncestor, root);

  const allBlocks = getDocumentBlocks(root);
  const blockIndex = blockEl ? allBlocks.indexOf(blockEl) : 0;

  // Prefix and suffix context calculation
  const blockText = blockEl ? (blockEl.textContent || '') : '';
  const textOffset = findTextOffsetInElement(blockEl || root, range.startContainer, range.startOffset);

  const prefixContext = blockText.slice(Math.max(0, textOffset - 40), textOffset);
  const suffixContext = blockText.slice(textOffset + quote.length, textOffset + quote.length + 40);

  return {
    blockIndex: blockIndex >= 0 ? blockIndex : 0,
    quote,
    prefixContext,
    suffixContext,
    textOffsetInBlock: textOffset
  };
}

/**
 * Resolves a RangeSelector back to a live DOM Range.
 */
export function deserializeRange(selector: RangeSelector, rootEl?: HTMLElement): Range | null {
  const root = rootEl || document.querySelector('.report-content') || document.querySelector('main') || document.body;
  const allBlocks = getDocumentBlocks(root);

  let targetBlock: Element | null = null;
  if (selector.blockIndex >= 0 && selector.blockIndex < allBlocks.length) {
    targetBlock = allBlocks[selector.blockIndex];
  }

  // 1. Try finding within targeted block
  if (targetBlock) {
    const range = locateQuoteInElement(targetBlock, selector);
    if (range) return range;
  }

  // 2. Fallback: Search across entire root if block index drifted
  return locateQuoteInElement(root, selector);
}

function findClosestBlock(node: Node, boundary: Element): Element | null {
  let curr: Node | null = node.nodeType === Node.TEXT_NODE ? node.parentElement : (node as Element);
  const blockTags = new Set(['P', 'LI', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'BLOCKQUOTE', 'TR', 'DIV', 'SECTION', 'ARTICLE']);

  while (curr && curr !== boundary && curr !== document.body) {
    if (curr.nodeType === Node.ELEMENT_NODE && blockTags.has((curr as Element).tagName)) {
      return curr as Element;
    }
    curr = curr.parentNode;
  }
  return boundary;
}

function getDocumentBlocks(root: Element): Element[] {
  return Array.from(root.querySelectorAll('p, li, h1, h2, h3, h4, h5, h6, blockquote, tr, pre'));
}

function findTextOffsetInElement(container: Element, targetNode: Node, targetOffset: number): number {
  let offset = 0;
  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let current: Node | null;

  while ((current = walker.nextNode())) {
    if (current === targetNode) {
      return offset + targetOffset;
    }
    offset += current.textContent?.length || 0;
  }
  return 0;
}

function locateQuoteInElement(container: Element, selector: RangeSelector): Range | null {
  const fullText = container.textContent || '';
  if (!fullText) return null;

  const quote = selector.quote;
  let matchIndex = -1;

  // Exact context match
  if (selector.prefixContext || selector.suffixContext) {
    const contextSearch = selector.prefixContext + quote + selector.suffixContext;
    const ctxIdx = fullText.indexOf(contextSearch);
    if (ctxIdx !== -1) {
      matchIndex = ctxIdx + selector.prefixContext.length;
    }
  }

  // Direct quote match if context failed
  if (matchIndex === -1) {
    matchIndex = fullText.indexOf(quote);
  }

  if (matchIndex === -1) return null;

  // Construct Range from character index
  return createRangeFromTextOffsets(container, matchIndex, matchIndex + quote.length);
}

function createRangeFromTextOffsets(container: Element, start: number, end: number): Range | null {
  const range = document.createRange();
  let currentOffset = 0;
  let startFound = false;

  const walker = document.createTreeWalker(container, NodeFilter.SHOW_TEXT);
  let node: Node | null;

  while ((node = walker.nextNode())) {
    const len = node.textContent?.length || 0;
    const nextOffset = currentOffset + len;

    if (!startFound && start >= currentOffset && start <= nextOffset) {
      range.setStart(node, start - currentOffset);
      startFound = true;
    }

    if (startFound && end >= currentOffset && end <= nextOffset) {
      range.setEnd(node, end - currentOffset);
      return range;
    }

    currentOffset = nextOffset;
  }

  return startFound ? range : null;
}

/**
 * Highlights a set of annotations using CSS Custom Highlight API (primary)
 * or safe leaf-node TreeWalker fallback (secondary).
 */
export class DocumentHighlighter {
  private supportsCssHighlight: boolean = false;

  constructor() {
    this.supportsCssHighlight = typeof (window as any).Highlight !== 'undefined' && typeof (CSS as any).highlights !== 'undefined';
  }

  applyHighlights(annotations: DocumentAnnotation[], rootEl?: HTMLElement) {
    this.clearHighlights(rootEl);

    if (this.supportsCssHighlight) {
      this.applyCssHighlights(annotations, rootEl);
    } else {
      this.applyDomFallbackHighlights(annotations, rootEl);
    }
  }

  clearHighlights(rootEl?: HTMLElement) {
    if (this.supportsCssHighlight) {
      const categories = ['correction', 'insight', 'feedback', 'commendation', 'question'];
      categories.forEach(cat => {
        (CSS as any).highlights.delete(`md-ann-${cat}`);
      });
    }

    const root = rootEl || document.querySelector('.report-content') || document.body;
    root.querySelectorAll('mark.md-annotation-mark').forEach(mark => {
      mark.replaceWith(...Array.from(mark.childNodes));
    });
    root.normalize();
  }

  private applyCssHighlights(annotations: DocumentAnnotation[], rootEl?: HTMLElement) {
    const byCategory: Record<string, Range[]> = {};

    for (const ann of annotations) {
      if (ann.resolved) continue;
      const range = deserializeRange(ann.range, rootEl);
      if (range) {
        if (!byCategory[ann.category]) byCategory[ann.category] = [];
        byCategory[ann.category].push(range);
      } else {
        ann.orphaned = true;
      }
    }

    for (const [cat, ranges] of Object.entries(byCategory)) {
      if (ranges.length > 0) {
        const highlightObj = new (window as any).Highlight(...ranges);
        (CSS as any).highlights.set(`md-ann-${cat}`, highlightObj);
      }
    }
  }

  private applyDomFallbackHighlights(annotations: DocumentAnnotation[], rootEl?: HTMLElement) {
    const root = rootEl || document.querySelector('.report-content') || document.body;

    for (const ann of annotations) {
      if (ann.resolved) continue;
      const range = deserializeRange(ann.range, root);
      if (!range) {
        ann.orphaned = true;
        continue;
      }

      this.wrapRangeSafe(range, ann);
    }
  }

  private wrapRangeSafe(range: Range, ann: DocumentAnnotation) {
    const common = range.commonAncestorContainer;
    const walker = document.createTreeWalker(
      common.nodeType === Node.TEXT_NODE ? common.parentElement || common : common,
      NodeFilter.SHOW_TEXT
    );

    const nodesToWrap: { node: Text; start: number; end: number }[] = [];
    let curr: Node | null;

    while ((curr = walker.nextNode())) {
      if (range.intersectsNode(curr) && curr.nodeType === Node.TEXT_NODE) {
        const textNode = curr as Text;
        const start = curr === range.startContainer ? range.startOffset : 0;
        const end = curr === range.endContainer ? range.endOffset : textNode.length;
        if (start < end) {
          nodesToWrap.push({ node: textNode, start, end });
        }
      }
    }

    // Wrap matched leaf segments
    for (const item of nodesToWrap) {
      const { node, start, end } = item;
      const text = node.textContent || '';
      const before = text.slice(0, start);
      const target = text.slice(start, end);
      const after = text.slice(end);

      const mark = document.createElement('mark');
      mark.className = `md-annotation-mark category-${ann.category}`;
      mark.setAttribute('data-ann-id', ann.id);
      mark.textContent = target;

      const parent = node.parentNode;
      if (!parent) continue;

      if (before) parent.insertBefore(document.createTextNode(before), node);
      parent.insertBefore(mark, node);
      if (after) parent.insertBefore(document.createTextNode(after), node);
      parent.removeChild(node);
    }
  }
}
