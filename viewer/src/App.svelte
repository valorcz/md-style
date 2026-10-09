<script lang="ts">
  import { onMount, mount } from 'svelte';
  import InspectorDrawer from './InspectorDrawer.svelte';
  import HudRibbon from './HudRibbon.svelte';
  import TableToolbar from './TableToolbar.svelte';

  export let title: string = '';
  export let enableHud: boolean = true;
  export let enableInspector: boolean = true;
  export let enableTableFilters: boolean = true;

  let knowledgeData: Record<string, any> = {};
  let i18nData: Record<string, string> = {};
  let selectedEntity: any = null;
  let isDrawerOpen: boolean = false;
  let hasSourceMarkdown: boolean = false;
  let sourceMarkdownText: string = '';

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

  function handleToggleInspector() {
    isDrawerOpen = !isDrawerOpen;
    if (isDrawerOpen && !selectedEntity) {
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
      isDrawerOpen = true;
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
      isDrawerOpen = true;
    }
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

  import mermaid from 'mermaid';
  import { renderMermaidSVG } from 'beautiful-mermaid';

  async function setupMermaidDiagrams() {
    const fallbackContainers = document.querySelectorAll('.mermaid-fallback');
    if (fallbackContainers.length === 0) return;

    const isDark = document.body.classList.contains('theme-forensic-cyber') ||
                   document.body.classList.contains('dark-theme') ||
                   document.documentElement.getAttribute('data-theme') === 'dark';
    const themeName = isDark ? 'zinc-dark' : 'zinc-light';

    for (const container of Array.from(fallbackContainers)) {
      const codeEl = container.querySelector('.mermaid');
      if (!codeEl) continue;
      const rawCode = (codeEl.textContent || '').trim();
      if (!rawCode) continue;

      let rendered = false;
      try {
        const svg = renderMermaidSVG(rawCode, {
          theme: themeName,
          transparent: true,
          font: 'Inter'
        });
        if (svg) {
          const wrapper = container.querySelector('.mermaid-svg-wrapper');
          if (wrapper) {
            wrapper.innerHTML = svg;
            container.classList.remove('mermaid-fallback');
            container.setAttribute('data-engine', 'beautiful-mermaid');
            rendered = true;
          }
        }
      } catch (bmErr) {
        // Schema not supported by beautiful-mermaid, fallback to standard mermaid.js
      }

      if (!rendered) {
        try {
          mermaid.initialize({
            startOnLoad: false,
            theme: isDark ? 'dark' : 'default',
            fontFamily: 'inherit',
            securityLevel: 'loose'
          });
          await mermaid.run({
            nodes: [codeEl as HTMLElement]
          });
          container.classList.remove('mermaid-fallback');
          container.setAttribute('data-engine', 'mermaid-js');
        } catch (mErr) {
          console.warn('[Viewer] Diagram render error:', mErr);
          const wrapper = container.querySelector('.mermaid-svg-wrapper');
          if (wrapper) {
            wrapper.innerHTML = `
              <div class="mermaid-error-card" style="padding: 12px; border: 1px solid #ef4444; border-radius: 6px; background: rgba(239, 68, 68, 0.08); color: #dc2626; font-family: monospace; font-size: 12px;">
                <strong>[Diagram Syntax Error]</strong>: ${mErr instanceof Error ? mErr.message : String(mErr)}
                <pre style="margin-top: 8px; color: inherit; white-space: pre-wrap; font-size: 11px;">${rawCode}</pre>
              </div>
            `;
          }
        }
      }
    }
  }

  import { Previewer } from 'pagedjs';

  let isPagedMode: boolean = false;
  let isPaginating: boolean = false;
  let pagedPreviewer: any = null;

  async function activatePagedMode() {
    if (isPaginating) return;
    const contentEl = document.querySelector('.report-content');
    if (!contentEl) return;

    isPaginating = true;
    document.body.classList.add('paged-view');

    let pagedRoot = document.getElementById('md-style-paged-root');
    if (!pagedRoot) {
      pagedRoot = document.createElement('div');
      pagedRoot.id = 'md-style-paged-root';
      document.body.appendChild(pagedRoot);
    }
    pagedRoot.style.display = 'block';
    pagedRoot.innerHTML = '';
    (contentEl as HTMLElement).style.display = 'none';

    try {
      pagedPreviewer = new Previewer();
      const inlineStyles = Array.from(document.querySelectorAll('style:not([data-pagedjs-inserted-styles], [data-pagedjs-ignore])'))
        .map(el => {
          const obj: Record<string, string> = {};
          obj[window.location.href] = el.textContent || '';
          return obj;
        });
      await pagedPreviewer.preview(contentEl.innerHTML, inlineStyles, pagedRoot);
      document.documentElement.dataset.pagedReady = 'true';
    } catch (err) {
      console.warn('[Viewer] Paged.js preview error:', err);
    } finally {
      isPaginating = false;
    }
  }

  function deactivatePagedMode() {
    document.body.classList.remove('paged-view');
    delete document.documentElement.dataset.pagedReady;
    const pagedRoot = document.getElementById('md-style-paged-root');
    if (pagedRoot) {
      pagedRoot.style.display = 'none';
      pagedRoot.innerHTML = '';
    }
    document.querySelectorAll('[data-pagedjs-inserted-styles]').forEach(el => el.remove());
    const contentEl = document.querySelector('.report-content') as HTMLElement;
    if (contentEl) {
      contentEl.style.display = '';
    }
  }

  async function handleTogglePaged() {
    isPagedMode = !isPagedMode;
    if (isPagedMode) {
      await activatePagedMode();
    } else {
      deactivatePagedMode();
    }
  }

  onMount(() => {
    loadKnowledgeData();
    loadI18nData();
    checkSourceMarkdown();
    setupMermaidDiagrams();

    if (window.location.hash.includes('paged') || document.body.classList.contains('paged-preview')) {
      handleTogglePaged();
    }

    const clickHandler = (e: MouseEvent) => {
      const target = (e.target as HTMLElement)?.closest('.inspectable') as HTMLElement;
      if (target) {
        e.preventDefault();
        handleEntityClick(target);
      }
    };

    document.addEventListener('click', clickHandler);
    setupTableToolbars();

    return () => {
      document.removeEventListener('click', clickHandler);
    };
  });
</script>

{#if enableHud}
  <HudRibbon
    {title}
    i18n={i18nData}
    {isPagedMode}
    entityCount={Object.keys(knowledgeData).length}
    on:togglePaged={handleTogglePaged}
    on:toggleInspector={handleToggleInspector}
  />
{/if}

{#if enableInspector}
  <InspectorDrawer
    bind:entity={selectedEntity}
    isOpen={isDrawerOpen}
    i18n={i18nData}
    allEntities={knowledgeData}
    {hasSourceMarkdown}
    onClose={() => (isDrawerOpen = false)}
    onSelectEntity={(e) => (selectedEntity = e)}
    onDownloadSource={handleDownloadSource}
  />
{/if}
