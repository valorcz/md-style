<script lang="ts">
  import { onMount, mount } from 'svelte';
  import InspectorDrawer from './InspectorDrawer.svelte';
  import HudRibbon from './HudRibbon.svelte';
  import TableToolbar from './TableToolbar.svelte';
  import FigureToolbar from './components/FigureToolbar.svelte';
  import FigureLightbox from './components/FigureLightbox.svelte';
  import AnnotationPopover from './annotations/AnnotationPopover.svelte';
  import MarginGutter from './annotations/MarginGutter.svelte';
  import { annotationStore } from './annotations/store';
  import { serializeRange } from './annotations/dom-anchor';

  export let title: string = '';
  export let enableHud: boolean = true;
  export let enableInspector: boolean = true;
  export let enableTableFilters: boolean = true;

  let selectionPopoverPos: { x: number; y: number } | null = null;
  let activeSelectedQuote: string = '';
  let activeSelectedRange: Range | null = null;

  let knowledgeData: Record<string, any> = {};
  let i18nData: Record<string, string> = {};
  let selectedEntity: any = null;
  let isDrawerOpen: boolean = false;
  let drawerTab: 'kb' | 'comments' = 'kb';
  let hasSourceMarkdown: boolean = false;
  let sourceMarkdownText: string = '';
  let activeLightboxFigure: { svgElement: SVGElement; title: string; id: string } | null = null;

  function loadKnowledgeData() {
    const scriptEl = document.getElementById('md-style-kb-data');
    if (scriptEl && scriptEl.textContent) {
      try {
        const parsed = JSON.parse(scriptEl.textContent);
        knowledgeData = parsed.entities || parsed;
      } catch (e) {
        console.warn('[Viewer] Could not parse embedded KB data:', e);
      }
    }
  }

  function loadI18nData() {
    const i18nEl = document.getElementById('md-style-i18n');
    if (i18nEl && i18nEl.textContent) {
      try {
        i18nData = JSON.parse(i18nEl.textContent);
      } catch (e) {
        console.warn('[Viewer] Could not parse embedded i18n data:', e);
      }
    }
  }

  function checkSourceMarkdown() {
    const mdScript = document.getElementById('md-style-source-markdown');
    if (mdScript && mdScript.textContent) {
      hasSourceMarkdown = true;
      sourceMarkdownText = mdScript.textContent.replace(/<\\\/script>/g, '<' + '/script>').trim();
    }
  }

  function handleDownloadSource() {
    if (!sourceMarkdownText) return;
    const blob = new Blob([sourceMarkdownText], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    const safeName = (title ? title.toLowerCase().replace(/[^a-z0-9_-]+/g, '-') : 'document') + '.md';
    a.download = safeName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function handleToggleInspector(tab?: 'kb' | 'comments' | CustomEvent<'kb' | 'comments'>) {
    const targetTab = typeof tab === 'string' ? tab : tab?.detail;
    if (targetTab) {
      if (isDrawerOpen && drawerTab === targetTab) {
        isDrawerOpen = false;
      } else {
        drawerTab = targetTab;
        if (targetTab === 'comments') {
          selectedEntity = null;
        }
        isDrawerOpen = true;
      }
    } else {
      isDrawerOpen = !isDrawerOpen;
    }
    document.body.classList.toggle('inspector-open', isDrawerOpen);
    if (isDrawerOpen && !selectedEntity && drawerTab === 'kb') {
      selectedEntity = null;
    }
  }

  function handleEntityClick(target: HTMLElement) {
    if (!enableInspector) return;
    const token = target.getAttribute('data-token') || target.getAttribute('data-value') || target.textContent?.trim();
    if (!token) return;

    let entity = knowledgeData[token];
    if (!entity) {
      const lowerToken = token.toLowerCase();
      for (const [k, v] of Object.entries(knowledgeData)) {
        if (k.toLowerCase() === lowerToken || (v as any).id?.toLowerCase() === lowerToken) {
          entity = v;
          break;
        }
      }
    }

    if (entity) {
      selectedEntity = entity;
    } else {
      selectedEntity = {
        id: token,
        title: token,
        type: target.getAttribute('data-type') || 'entity',
        domain: target.getAttribute('data-domain') || 'general',
        severity: 'INFO',
        badge: i18nData.discovered || 'DISCOVERED TOKEN',
        summary: 'Entity referenced in report text.'
      };
    }
    drawerTab = 'kb';
    isDrawerOpen = true;
    document.body.classList.add('inspector-open');
  }

  function setupTableToolbars() {
    if (!enableTableFilters) return;
    // Skip SVJ housing association themes (agendas, ballots)
    if (document.body.className.includes('theme-svj')) return;

    const tables = document.querySelectorAll('table');
    tables.forEach(table => {
      const tbody = table.querySelector('tbody');
      const rowCount = tbody ? tbody.querySelectorAll('tr').length : 0;
      const isTimeline = table.classList.contains('table-timeline');

      // Only mount on large tables (>= 4 rows) or timeline tables
      if (rowCount < 4 && !isTimeline) return;

      const parent = table.parentElement;
      if (!parent || parent.querySelector('.table-toolbar-container')) return;

      const container = document.createElement('div');
      container.className = 'table-toolbar-container';
      parent.insertBefore(container, table);

      mount(TableToolbar, {
        target: container,
        props: {
          tableElement: table as HTMLTableElement,
          i18n: i18nData
        }
      });
    });
  }

  function setupFigureToolbars() {
    const figures = document.querySelectorAll<HTMLElement>(
      'figure.figure-container, figure.svg-figure, figure.mermaid-diagram, figure.d2-diagram'
    );

    figures.forEach(figure => {
      if (figure.querySelector('.figure-toolbar-mount')) return;
      const svgEl = figure.querySelector('svg');
      if (!svgEl) return;

      figure.style.position = 'relative';
      const container = document.createElement('div');
      container.className = 'figure-toolbar-mount';
      figure.appendChild(container);

      mount(FigureToolbar, {
        target: container,
        props: {
          figureElement: figure,
          i18n: i18nData,
          onOpenLightbox: (detail: { svgElement: SVGElement; title: string; id: string }) => {
            activeLightboxFigure = detail;
          }
        }
      });
    });
  }

  import * as pele from 'pele';

  async function setupMermaidDiagrams() {
    const fallbackContainers = document.querySelectorAll('.mermaid-fallback');
    if (fallbackContainers.length === 0) return;

    for (const container of Array.from(fallbackContainers)) {
      const codeEl = container.querySelector('.mermaid');
      if (!codeEl) continue;
      const rawCode = (codeEl.textContent || '').trim();
      if (!rawCode) continue;

      try {
        const res = pele.render(rawCode);
        if (res && res.svg) {
          const wrapper = container.querySelector('.mermaid-svg-wrapper');
          if (wrapper) {
            wrapper.innerHTML = res.svg;
            container.classList.remove('mermaid-fallback');
            container.setAttribute('data-engine', 'pele');
          }
        }
      } catch (pErr) {
        console.warn('[Viewer] Diagram render error:', pErr);
        const wrapper = container.querySelector('.mermaid-svg-wrapper');
        if (wrapper) {
          wrapper.innerHTML = `
            <div class="mermaid-error-card" style="padding: 12px; border: 1px solid #ef4444; border-radius: 6px; background: rgba(239, 68, 68, 0.08); color: #dc2626; font-family: monospace; font-size: 12px;">
              <strong>[Diagram Syntax Error]</strong>: ${pErr instanceof Error ? pErr.message : String(pErr)}
              <pre style="margin-top: 8px; color: inherit; white-space: pre-wrap; font-size: 11px;">${rawCode}</pre>
            </div>
          `;
        }
      }
    }
  }

  import { Previewer } from 'pagedjs';
  import { registerUnifiedHandlers, getEmbeddedPrintTemplates } from './paged/paged-handlers';

  let isPagedMode: boolean = false;
  let isPaginating: boolean = false;
  let hasRenderedPaged: boolean = false;

  async function handleTogglePaged() {
    isPagedMode = !isPagedMode;

    if (isPagedMode) {
      document.body.classList.add('paged-view');

      if (!hasRenderedPaged) {
        isPaginating = true;
        registerUnifiedHandlers();

        let root = document.getElementById('md-style-paged-root');
        if (!root) {
          root = document.createElement('div');
          root.id = 'md-style-paged-root';
          document.body.appendChild(root);
        }

        const contentEl =
          document.querySelector('.report-container') ||
          document.querySelector('main:not(#md-style-paged-root)') ||
          document.querySelector('.report-content');

        if (contentEl) {
          const clone = contentEl.cloneNode(true) as HTMLElement;

          try {
            const templates = getEmbeddedPrintTemplates();
            const previewer = new Previewer();

            const inlinePageStyles: Record<string, string> = {};
            if (templates) {
              const top = templates.marginTop ? `${templates.marginTop}in` : '22mm';
              const right = templates.marginRight ? `${templates.marginRight}in` : '18mm';
              const bottom = templates.marginBottom ? `${templates.marginBottom}in` : '22mm';
              const left = templates.marginLeft ? `${templates.marginLeft}in` : '18mm';
              inlinePageStyles['md-style-page-geom'] = `@page { size: A4; margin: ${top} ${right} ${bottom} ${left}; }`;
            }

            await previewer.preview(clone, [inlinePageStyles], root);
            hasRenderedPaged = true;
          } catch (err) {
            console.error('[Paged] Pagination failed:', err);
          } finally {
            isPaginating = false;
          }
        } else {
          isPaginating = false;
        }
      }
    } else {
      document.body.classList.remove('paged-view');
    }
  }

  onMount(() => {
    loadKnowledgeData();
    loadI18nData();
    checkSourceMarkdown();
    setupMermaidDiagrams().then(() => {
      setupFigureToolbars();
    });

    if (window.location.hash.includes('paged') || document.body.classList.contains('paged-preview')) {
      handleTogglePaged();
    }

    annotationStore.init();

    const handleSelectionChange = () => {
      const sel = window.getSelection();
      if (!sel || sel.isCollapsed || !sel.toString().trim()) {
        const popover = document.querySelector('.annotation-popover');
        if (popover && (popover.contains(document.activeElement) || popover.querySelector('.popover-composer'))) {
          return;
        }
        selectionPopoverPos = null;
        activeSelectedRange = null;
        activeSelectedQuote = '';
        return;
      }

      // Check if selection is within report content
      const root = document.querySelector('.report-content') || document.querySelector('main');
      if (!root) return;

      const range = sel.getRangeAt(0);
      if (!root.contains(range.commonAncestorContainer)) return;

      const rect = range.getBoundingClientRect();
      activeSelectedRange = range;
      activeSelectedQuote = sel.toString().trim();
      selectionPopoverPos = {
        x: rect.right + 12,
        y: rect.top
      };
    };

    document.addEventListener('selectionchange', handleSelectionChange);

    const clickHandler = (e: MouseEvent) => {
      // Disambiguate: if text is currently highlighted by the user, do not open inspectable entity drawer
      const sel = window.getSelection();
      if (sel && sel.toString().trim().length > 0) return;

      // Handle clicking an annotation mark
      const annMark = (e.target as HTMLElement)?.closest('.md-annotation-mark') as HTMLElement;
      if (annMark) {
        const annId = annMark.getAttribute('data-ann-id');
        if (annId) {
          annotationStore.setActive(annId);
          selectedEntity = null;
          drawerTab = 'comments';
          isDrawerOpen = true;
          document.body.classList.add('inspector-open');
          return;
        }
      }

      const target = (e.target as HTMLElement)?.closest('.inspectable') as HTMLElement;
      if (target) {
        e.preventDefault();
        handleEntityClick(target);
      }
    };

    document.addEventListener('click', clickHandler);
    setupTableToolbars();
    setupFigureToolbars();

    return () => {
      document.removeEventListener('click', clickHandler);
      document.removeEventListener('selectionchange', handleSelectionChange);
    };
  });

  function handleCreateAnnotation(event: CustomEvent<any>) {
    if (!activeSelectedRange) return;
    const selector = serializeRange(activeSelectedRange);
    if (!selector) return;

    annotationStore.addAnnotation({
      category: event.detail.category,
      text: event.detail.text,
      author: event.detail.author,
      range: selector
    });

    window.getSelection()?.removeAllRanges();
    selectionPopoverPos = null;
    activeSelectedRange = null;
    activeSelectedQuote = '';
  }
</script>

{#if isPaginating}
  <div class="paged-loading-overlay">
    <div class="paged-loading-spinner"></div>
    <span>{i18nData['paginating'] || 'Paginating A4 sheets...'}</span>
  </div>
{/if}

{#if enableHud}
  <HudRibbon
    {title}
    i18n={i18nData}
    {isPagedMode}
    isInspectorOpen={isDrawerOpen}
    activeDrawerTab={drawerTab}
    entityCount={Object.keys(knowledgeData).length}
    commentCount={$annotationStore.annotations.length}
    educativeMode={$annotationStore.educativeMode}
    on:togglePaged={handleTogglePaged}
    on:toggleInspector={handleToggleInspector}
    on:toggleEducativeMode={() => annotationStore.toggleEducativeMode()}
  />
{/if}

{#if $annotationStore.educativeMode && !isPagedMode}
  <MarginGutter
    annotations={$annotationStore.annotations}
    activeAnnotationId={$annotationStore.activeAnnotationId}
  />
{/if}

{#if selectionPopoverPos && activeSelectedQuote}
  <AnnotationPopover
    position={selectionPopoverPos}
    quoteText={activeSelectedQuote}
    on:create={handleCreateAnnotation}
    on:cancel={() => {
      selectionPopoverPos = null;
      activeSelectedQuote = '';
      activeSelectedRange = null;
    }}
  />
{/if}

{#if enableInspector}
  <InspectorDrawer
    bind:entity={selectedEntity}
    bind:activeTab={drawerTab}
    isOpen={isDrawerOpen}
    i18n={i18nData}
    allEntities={knowledgeData}
    {hasSourceMarkdown}
    onClose={() => {
      isDrawerOpen = false;
      document.body.classList.remove('inspector-open');
    }}
    onSelectEntity={(e) => (selectedEntity = e)}
    onDownloadSource={handleDownloadSource}
  />
{/if}

<FigureLightbox
  isOpen={activeLightboxFigure !== null}
  svgElement={activeLightboxFigure?.svgElement || null}
  title={activeLightboxFigure?.title || ''}
  id={activeLightboxFigure?.id || ''}
  i18n={i18nData}
  onClose={() => { activeLightboxFigure = null; }}
/>
