<script lang="ts">
  import { onMount, mount } from 'svelte';
  import InspectorDrawer from './InspectorDrawer.svelte';
  import HudRibbon from './HudRibbon.svelte';
  import SidebarToc from './components/SidebarToc.svelte';
  import TableToolbar from './TableToolbar.svelte';
  import FigureToolbar from './components/FigureToolbar.svelte';
  import FigureLightbox from './components/FigureLightbox.svelte';
  import EntityHoverCard from './components/EntityHoverCard.svelte';
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
  let isTocOpen: boolean = false;
  let drawerTab: 'kb' | 'comments' = 'kb';

  let hoverCardEntity: any = null;
  let hoverCardPos: { x: number; y: number } | null = null;
  let isHoverCardOpen: boolean = false;
  let hoverCardTimeout: any = null;
  let hoverCardCloseTimeout: any = null;

  $: if (typeof document !== 'undefined') {
    document.body.classList.toggle('toc-docked', isTocOpen);
  }
  let hasSourceMarkdown: boolean = false;
  let sourceMarkdownText: string = '';
  let activeLightboxFigure: { svgElement: SVGElement; title: string; id: string } | null = null;
  let customComponentCount: number = 0;

  function resolveEntity(token: string, target?: HTMLElement): any {
    if (!token) return null;
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
    if (entity) return entity;
    return {
      id: token,
      title: token,
      type: target?.getAttribute('data-type') || 'Pojem',
      domain: target?.getAttribute('data-domain') || 'general',
      severity: 'INFO',
      summary: target?.getAttribute('title') || 'Entita v textu dokumentu.'
    };
  }

  function handleOpenEntityDetails(entity: any) {
    isHoverCardOpen = false;
    hoverCardEntity = null;
    selectedEntity = entity;
    drawerTab = 'kb';
    const wasOpen = isDrawerOpen;
    isDrawerOpen = true;
    document.body.classList.add('inspector-open');
    if (!wasOpen) handleInspectorStateChange(true);
  }

  function handleHoverCardMouseEnter() {
    if (hoverCardCloseTimeout) {
      clearTimeout(hoverCardCloseTimeout);
      hoverCardCloseTimeout = null;
    }
  }

  function handleHoverCardMouseLeave() {
    hoverCardCloseTimeout = setTimeout(() => {
      isHoverCardOpen = false;
      hoverCardEntity = null;
    }, 150);
  }

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

  let wasTocOpenBeforeInspector: boolean = false;

  function handleInspectorStateChange(opening: boolean) {
    if (opening) {
      if (typeof window !== 'undefined' && window.innerWidth < 1600) {
        if (isTocOpen) {
          wasTocOpenBeforeInspector = true;
          isTocOpen = false;
        }
      }
    } else {
      if (wasTocOpenBeforeInspector) {
        isTocOpen = true;
        wasTocOpenBeforeInspector = false;
      }
    }
  }

  function handleToggleInspector(tab?: 'kb' | 'comments' | CustomEvent<'kb' | 'comments'>) {
    const targetTab = typeof tab === 'string' ? tab : tab?.detail;
    if (targetTab) {
      if (isDrawerOpen && drawerTab === targetTab) {
        isDrawerOpen = false;
        document.body.classList.remove('inspector-open');
        handleInspectorStateChange(false);
      } else {
        drawerTab = targetTab;
        if (targetTab === 'comments') {
          selectedEntity = null;
        }
        if (!isDrawerOpen) {
          isDrawerOpen = true;
          document.body.classList.add('inspector-open');
          handleInspectorStateChange(true);
        }
      }
    } else {
      isDrawerOpen = !isDrawerOpen;
      document.body.classList.toggle('inspector-open', isDrawerOpen);
      handleInspectorStateChange(isDrawerOpen);
    }
    if (isDrawerOpen && !selectedEntity && drawerTab === 'kb') {
      selectedEntity = null;
    }
  }

  function handleEntityClick(target: HTMLElement) {
    if (!enableInspector) return;
    const token = target.getAttribute('data-token') || target.getAttribute('data-value') || target.textContent?.trim();
    if (!token) return;

    if (hoverCardTimeout) clearTimeout(hoverCardTimeout);
    isHoverCardOpen = false;
    hoverCardEntity = null;

    selectedEntity = resolveEntity(token, target);
    drawerTab = 'kb';
    const wasOpen = isDrawerOpen;
    isDrawerOpen = true;
    document.body.classList.add('inspector-open');
    if (!wasOpen) handleInspectorStateChange(true);
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

  import { getSvgDimensions } from './figure/figure-geometry';

  function setupFigureToolbars() {
    const figures = document.querySelectorAll<HTMLElement>(
      'figure.doc-figure, figure.figure-container, figure.svg-figure, figure.mermaid-diagram, figure.d2-diagram'
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
    const fallbackContainers = document.querySelectorAll<HTMLElement>('.mermaid-fallback');
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

            // Apply unified geometry dataset and optical budget attributes
            const svgEl = wrapper.querySelector('svg');
            if (svgEl) {
              const dims = getSvgDimensions(svgEl);
              container.classList.add(`orientation-${dims.orientation}`);
              container.setAttribute('data-orientation', dims.orientation);
              container.setAttribute('data-natural-w', String(Math.round(dims.w * 10) / 10));
              container.setAttribute('data-natural-h', String(Math.round(dims.h * 10) / 10));
              container.setAttribute('data-aspect-ratio', String(Math.round(dims.aspectRatio * 100) / 100));

              if (dims.orientation === 'portrait') {
                container.classList.add('diagram-tall');
              } else if (dims.orientation === 'ultrawide') {
                container.classList.add('diagram-wide');
              }

              // Optical sizing: cap width proportionally if height exceeds 520px
              const maxH = 520;
              const padding = 48;
              let optWidth = dims.w + padding;
              if (dims.h > maxH) {
                optWidth = Math.min(dims.w, maxH * dims.aspectRatio) + padding;
              }
              container.style.setProperty('--fig-natural-w', `${dims.w}px`);
              container.style.setProperty('--fig-natural-h', `${dims.h}px`);
              container.style.setProperty('max-width', `min(100%, ${Math.round(optWidth)}px)`);
            }
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
    customComponentCount = document.querySelectorAll('.doc-component-mount').length;

    // Expose toolbar setup so late-mounted components can register toolbars
    const viewerObj = (window as any).MdStyleViewer || {};
    viewerObj.setupFigureToolbars = setupFigureToolbars;
    (window as any).MdStyleViewer = viewerObj;

    document.addEventListener('md-style:components-mounted', () => {
      setTimeout(setupFigureToolbars, 50);
    });

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

    const handleKeydown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || (e.target as HTMLElement)?.isContentEditable) return;
      if (e.key === 't' || e.key === 'T') {
        if (!e.ctrlKey && !e.metaKey && !e.altKey) {
          e.preventDefault();
          isTocOpen = !isTocOpen;
        }
      }
    };

    const mouseOverHandler = (e: MouseEvent) => {
      if (!enableInspector) return;
      const target = (e.target as HTMLElement)?.closest('.inspectable') as HTMLElement;
      if (target) {
        if (hoverCardCloseTimeout) {
          clearTimeout(hoverCardCloseTimeout);
          hoverCardCloseTimeout = null;
        }
        const token = target.getAttribute('data-token') || target.getAttribute('data-value') || target.textContent?.trim();
        if (!token) return;

        const ent = resolveEntity(token, target);
        if (ent) {
          if (hoverCardTimeout) clearTimeout(hoverCardTimeout);
          hoverCardTimeout = setTimeout(() => {
            const rect = target.getBoundingClientRect();
            hoverCardEntity = ent;
            hoverCardPos = { x: rect.left, y: rect.bottom };
            isHoverCardOpen = true;
          }, 150);
        }
      }
    };

    const mouseOutHandler = (e: MouseEvent) => {
      const target = (e.target as HTMLElement)?.closest('.inspectable') as HTMLElement;
      if (target) {
        if (hoverCardTimeout) {
          clearTimeout(hoverCardTimeout);
          hoverCardTimeout = null;
        }
        hoverCardCloseTimeout = setTimeout(() => {
          isHoverCardOpen = false;
          hoverCardEntity = null;
        }, 200);
      }
    };

    document.addEventListener('keydown', handleKeydown);
    document.addEventListener('click', clickHandler);
    document.addEventListener('mouseover', mouseOverHandler);
    document.addEventListener('mouseout', mouseOutHandler);
    setupTableToolbars();
    setupFigureToolbars();

    return () => {
      document.removeEventListener('keydown', handleKeydown);
      document.removeEventListener('click', clickHandler);
      document.removeEventListener('mouseover', mouseOverHandler);
      document.removeEventListener('mouseout', mouseOutHandler);
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
  <SidebarToc
    isOpen={isTocOpen}
    isInspectorOpen={isDrawerOpen}
    i18n={i18nData}
    onClose={() => {
      isTocOpen = false;
      wasTocOpenBeforeInspector = false;
    }}
  />
  <HudRibbon
    {title}
    i18n={i18nData}
    {isPagedMode}
    isInspectorOpen={isDrawerOpen}
    {isTocOpen}
    activeDrawerTab={drawerTab}
    entityCount={Object.keys(knowledgeData).length}
    commentCount={$annotationStore.annotations.length}
    componentCount={customComponentCount}
    educativeMode={$annotationStore.educativeMode}
    {hasSourceMarkdown}
    on:togglePaged={handleTogglePaged}
    on:toggleInspector={handleToggleInspector}
    on:toggleToc={() => {
      isTocOpen = !isTocOpen;
      if (!isTocOpen) wasTocOpenBeforeInspector = false;
    }}
    on:toggleEducativeMode={() => annotationStore.toggleEducativeMode()}
    on:downloadSource={handleDownloadSource}
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
      handleInspectorStateChange(false);
    }}
    onSelectEntity={(e) => (selectedEntity = e)}
    onDownloadSource={handleDownloadSource}
  />
  <EntityHoverCard
    entity={hoverCardEntity}
    position={hoverCardPos}
    isOpen={isHoverCardOpen}
    onOpenDetails={handleOpenEntityDetails}
    onClose={() => { isHoverCardOpen = false; hoverCardEntity = null; }}
    on:mouseenter={handleHoverCardMouseEnter}
    on:mouseleave={handleHoverCardMouseLeave}
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

<style>
  /* Clean reading flow: Spine on left margin, annotations on right margin */
</style>
