<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';

  export let title: string = '';
  export let i18n: Record<string, string> = {};
  export let isPagedMode: boolean = false;

  export let entityCount: number = 0;

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
      <button class="action-btn" on:click={() => dispatch('toggleInspector')} title="Inspect Knowledge Entities & Metadata">
        🔍 {entityCount > 0 ? `Entities (${entityCount})` : 'Inspector'}
      </button>
      <button class="action-btn theme-toggle-btn" on:click={toggleTheme} title="Toggle Dark / Light theme">
        {isDarkMode ? '🌙 Dark' : '☀️ Light'}
      </button>
      <button class="action-btn" on:click={togglePaged} title={isPagedMode ? (i18n['ui.web_view'] || 'Web View') : (i18n['ui.paged_view'] || 'Paged View')}>
        {isPagedMode ? '🖥️ ' + (i18n['ui.web_view'] || 'Web View') : '📄 ' + (i18n['ui.paged_view'] || 'Paged View')}
      </button>
      <button class="action-btn" on:click={handlePrint} title={i18n['ui.print'] || 'Print / PDF'}>
        🖨️ {i18n['ui.print'] || 'Print'}
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
    z-index: 9999;
    background: rgba(15, 23, 42, 0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
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
  .action-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    border-color: rgba(255, 255, 255, 0.25);
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
  @media print {
    .hud-container {
      display: none !important;
    }
  }
</style>
