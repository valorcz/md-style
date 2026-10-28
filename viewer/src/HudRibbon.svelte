<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import Icon from './components/Icon.svelte';

  export let title: string = '';
  export let i18n: Record<string, string> = {};
  export let isPagedMode: boolean = false;
  export let isInspectorOpen: boolean = false;
  export let activeDrawerTab: 'kb' | 'comments' = 'kb';

  export let entityCount: number = 0;
  export let commentCount: number = 0;
  export let educativeMode: boolean = true;
  export let onTogglePaged: (() => void) | undefined = undefined;
  export let onToggleInspector: (() => void) | undefined = undefined;

  const dispatch = createEventDispatcher();
  let progress: number = 0;
  let activeSection: string = '';
  let isDarkMode: boolean = true;

  function updateScrollState() {
    // 1. Reading progress
    const totalHeight = document.documentElement.scrollHeight - window.innerHeight;
    if (totalHeight > 0) {
      progress = Math.min(100, Math.max(0, (window.scrollY / totalHeight) * 100));
    }

    // 2. Active section detection (H2 / H3)
    const headings = Array.from(document.querySelectorAll('main h2, main h3, .report-content h2, .report-content h3'));
    if (headings.length > 0) {
      let currentHeading = '';
      for (const h of headings) {
        const rect = h.getBoundingClientRect();
        if (rect.top <= 120) {
          currentHeading = h.textContent?.trim() || '';
        } else {
          break;
        }
      }
      activeSection = currentHeading;
    }
  }

  function toggleTheme() {
    isDarkMode = !isDarkMode;
    const themeStr = isDarkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', themeStr);
    document.documentElement.dataset.theme = themeStr;
  }

  function handlePrint() {
    window.print();
  }

  function togglePaged() {
    if (onTogglePaged) onTogglePaged();
    dispatch('togglePaged');
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  onMount(() => {
    // Initial theme detection
    const currentTheme = document.documentElement.getAttribute('data-theme') || document.documentElement.dataset.theme;
    if (currentTheme) {
      isDarkMode = currentTheme === 'dark';
    } else {
      isDarkMode = !document.body.classList.contains('theme-forensic-dossier') && !document.body.classList.contains('theme-svj-invitation');
      document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    }

    window.addEventListener('scroll', updateScrollState, { passive: true });
    updateScrollState();
    return () => {
      window.removeEventListener('scroll', updateScrollState);
    };
  });
</script>

<aside id="viewer-hud-ribbon" class="hud-container" aria-label="Document HUD">
  <div class="progress-bar-track">
    <div class="progress-bar-fill" style="width: {progress}%;"></div>
  </div>
  <div class="hud-content">
    <div class="hud-left">
      <button class="hud-brand" on:click={scrollToTop} title={i18n['ui.scroll_top'] || 'Scroll to top'}>
        <span class="hud-dot"></span>
        <span class="hud-title">{title || document.title || 'REPORT'}</span>
      </button>
      {#if activeSection}
        <span class="hud-sep">›</span>
        <span class="hud-active-section">{activeSection}</span>
      {/if}
    </div>
    <div class="hud-right">
      <button
        class="action-btn"
        class:active={educativeMode}
        on:click={() => dispatch('toggleEducativeMode')}
        title={educativeMode ? 'Educative Mode Active (Comments Visible)' : 'Reader Mode (Comments Hidden)'}
      >
        <Icon name="academic" size={14} />
        <span>{educativeMode ? 'Educative' : 'Reader'}</span>
      </button>
      <button
        class="action-btn"
        class:active={isInspectorOpen && activeDrawerTab === 'kb'}
        on:click={() => dispatch('toggleInspector', 'kb')}
        title="Inspect Knowledge Entities"
      >
        <Icon name="layers" size={14} />
        <span>{entityCount > 0 ? `Entities (${entityCount})` : 'Entities'}</span>
      </button>
      <button
        class="action-btn"
        class:active={isInspectorOpen && activeDrawerTab === 'comments'}
        on:click={() => dispatch('toggleInspector', 'comments')}
        title="View Review Comments & Notes"
      >
        <Icon name="message-square" size={14} />
        <span class="sr-only">💬</span>
        <span>{commentCount > 0 ? `Notes (${commentCount})` : 'Notes'}</span>
      </button>
      <button class="action-btn theme-toggle-btn" on:click={toggleTheme} title="Toggle Dark / Light theme">
        <Icon name={isDarkMode ? 'moon' : 'sun'} size={14} />
        <span>{isDarkMode ? 'Dark' : 'Light'}</span>
      </button>
      <button class="action-btn" on:click={togglePaged} title={isPagedMode ? (i18n['ui.web_view'] || 'Web View') : (i18n['ui.paper_view'] || i18n['ui.paged_view'] || 'Paper View')}>
        <Icon name={isPagedMode ? 'monitor' : 'file-text'} size={14} />
        <span>{isPagedMode ? (i18n['ui.web_view'] || 'Web View') : (i18n['ui.paper_view'] || i18n['ui.paged_view'] || 'Paper View')}</span>
      </button>
      <button class="action-btn" on:click={handlePrint} title={i18n['ui.print'] || 'Print / PDF'}>
        <Icon name="printer" size={14} />
        <span>{i18n['ui.print'] || 'Print'}</span>
      </button>
    </div>
  </div>
</aside>

<style>
  .hud-container {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 10000;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    font-family: var(--font-mono, "JetBrains Mono", "Cascadia Code", "Fira Code", monospace);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
  }
  .hud-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.25rem;
    height: 40px;
    box-sizing: border-box;
  }
  .hud-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }
  .hud-brand {
    background: transparent;
    border: none;
    color: inherit;
    display: flex;
    align-items: center;
    gap: 0.5rem;
    cursor: pointer;
    padding: 0;
    text-align: left;
    white-space: nowrap;
  }
  .hud-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #00f0ff;
    box-shadow: 0 0 8px #00f0ff;
    flex-shrink: 0;
  }
  .hud-title {
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #f8fafc;
    text-transform: uppercase;
  }
  .hud-sep {
    color: #64748b;
    font-size: 0.85rem;
    user-select: none;
  }
  .hud-active-section {
    font-size: 0.8rem;
    color: #94a3b8;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 400px;
  }
  .hud-right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }
  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #f1f5f9;
    padding: 0.22rem 0.65rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s;
    user-select: none;
  }
  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }
  .action-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.25);
  }
  .action-btn.active {
    background: rgba(56, 189, 248, 0.22);
    border-color: #38bdf8;
    color: #38bdf8;
    box-shadow: 0 0 10px rgba(56, 189, 248, 0.35);
  }
  :global([data-theme="light"]) .hud-container,
  :global(body.light-theme) .hud-container {
    background: rgba(255, 255, 255, 0.94);
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06);
  }
  :global([data-theme="light"]) .hud-title,
  :global(body.light-theme) .hud-title {
    color: #0f172a;
  }
  :global([data-theme="light"]) .hud-active-section,
  :global(body.light-theme) .hud-active-section {
    color: #475569;
  }
  :global([data-theme="light"]) .action-btn,
  :global(body.light-theme) .action-btn {
    background: rgba(0, 0, 0, 0.05);
    border: 1px solid rgba(0, 0, 0, 0.12);
    color: #1e293b;
  }
  :global([data-theme="light"]) .action-btn:hover,
  :global(body.light-theme) .action-btn:hover {
    background: rgba(0, 0, 0, 0.09);
    border-color: rgba(0, 0, 0, 0.2);
  }
  :global([data-theme="light"]) .action-btn.active,
  :global(body.light-theme) .action-btn.active {
    background: rgba(2, 132, 199, 0.12);
    border-color: #0284c7;
    color: #0284c7;
    box-shadow: 0 0 8px rgba(2, 132, 199, 0.2);
  }
  .theme-toggle-btn {
    background: rgba(255, 255, 255, 0.12);
  }
  .progress-bar-track {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: rgba(255, 255, 255, 0.05);
  }
  .progress-bar-fill {
    height: 100%;
    background: #00f0ff;
    transition: width 0.05s linear;
  }
  :global(body.theme-forensic-dossier) .hud-container {
    background: rgba(255, 255, 255, 0.94);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    border-bottom: 1px solid #cbd5e1;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.06);
    color: #0f172a;
  }
  :global(body.theme-forensic-dossier) .hud-title {
    color: #0f172a;
    font-weight: 700;
  }
  :global(body.theme-forensic-dossier) .hud-dot {
    background: #0284c7;
    box-shadow: 0 0 6px rgba(2, 132, 199, 0.5);
  }
  :global(body.theme-forensic-dossier) .hud-sep {
    color: #94a3b8;
  }
  :global(body.theme-forensic-dossier) .hud-active-section {
    color: #0284c7;
    font-weight: 600;
  }
  :global(body.theme-forensic-dossier) .action-btn {
    background: #f8fafc;
    border: 1px solid #cbd5e1;
    color: #334155;
  }
  :global(body.theme-forensic-dossier) .action-btn:hover {
    background: #f1f5f9;
    border-color: #94a3b8;
    color: #0f172a;
  }
  :global(body.theme-forensic-dossier) .action-btn.active {
    background: rgba(2, 132, 199, 0.1);
    border-color: #0284c7;
    color: #0284c7;
  }
  :global(body.theme-forensic-dossier) .progress-bar-fill {
    background: linear-gradient(90deg, #0284c7, #38bdf8);
  }
  @media print {
    .hud-container {
      display: none !important;
    }
  }
</style>
