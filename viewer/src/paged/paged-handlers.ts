import { Handler, registerHandlers } from 'pagedjs';

export interface PrintTemplates {
  headerTemplate: string;
  footerTemplate: string;
  showFirstHeader?: boolean;
  showFirstFooter?: boolean;
  marginTop?: number;
  marginBottom?: number;
  marginLeft?: number;
  marginRight?: number;
}

export function getEmbeddedPrintTemplates(): PrintTemplates | null {
  const el = document.getElementById('md-style-print-templates');
  if (el && el.textContent) {
    try {
      return JSON.parse(el.textContent);
    } catch (e) {
      console.warn('[Paged] Failed to parse #md-style-print-templates:', e);
    }
  }
  return null;
}

export class UnifiedHeaderFooterHandler extends Handler {
  private olCounters: Map<string, number> = new Map();

  constructor(chunker: any, polisher: any, caller: any) {
    super(chunker, polisher, caller);
    this.olCounters = new Map();
  }

  beforeParsed(content: HTMLElement) {
    // 1. Tag all ordered lists with unique identifiers to track continuation across page splits
    let listCounter = 0;
    const lists = content.querySelectorAll('ol');
    lists.forEach((ol) => {
      if (!ol.hasAttribute('data-ol-id')) {
        ol.setAttribute('data-ol-id', `list-${++listCounter}`);
      }
    });
  }

  afterPageLayout(pageElement: HTMLElement, _page: any, _breakToken: any, _chunker: any) {
    // Fix ordered list numbering continuation across page boundaries
    const pageLists = pageElement.querySelectorAll('ol');
    pageLists.forEach((ol) => {
      const listId = ol.getAttribute('data-ol-id');
      if (listId) {
        if (this.olCounters.has(listId)) {
          const prevCount = this.olCounters.get(listId)!;
          ol.setAttribute('start', String(prevCount + 1));
          const currentCount = ol.querySelectorAll(':scope > li').length;
          this.olCounters.set(listId, prevCount + currentCount);
        } else {
          const initialStart = parseInt(ol.getAttribute('start') || '1', 10);
          const currentCount = ol.querySelectorAll(':scope > li').length;
          this.olCounters.set(listId, (initialStart - 1) + currentCount);
        }
      }
    });
  }

  afterRendered(pages: any[], _chunker: any) {
    const templates = getEmbeddedPrintTemplates();
    if (!templates || !pages) return;

    const total = pages.length;

    pages.forEach((page: any, index: number) => {
      const pageElement = page.element;
      if (!pageElement) return;

      const isFirstPage = index === 0;
      const showHeader = !isFirstPage || (templates.showFirstHeader ?? true);
      const showFooter = !isFirstPage || (templates.showFirstFooter ?? true);

      // Top margin / header
      const topMargin = pageElement.querySelector('.pagedjs_margin-top');
      if (topMargin) {
        if (showHeader && templates.headerTemplate) {
          topMargin.innerHTML = templates.headerTemplate;
        } else {
          topMargin.innerHTML = '';
        }
      }

      // Bottom margin / footer
      const bottomMargin = pageElement.querySelector('.pagedjs_margin-bottom');
      if (bottomMargin) {
        if (showFooter && templates.footerTemplate) {
          bottomMargin.innerHTML = templates.footerTemplate;
          const pageNumEl = bottomMargin.querySelector('.pageNumber');
          if (pageNumEl) {
            pageNumEl.textContent = String(index + 1);
          }
          const totalPagesEl = bottomMargin.querySelector('.totalPages');
          if (totalPagesEl) {
            totalPagesEl.textContent = String(total);
          }
        } else {
          bottomMargin.innerHTML = '';
        }
      }
    });
  }
}

let isRegistered = false;
export function registerUnifiedHandlers() {
  if (!isRegistered) {
    registerHandlers(UnifiedHeaderFooterHandler);
    isRegistered = true;
  }
}
