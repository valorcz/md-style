<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import Icon from './components/Icon.svelte';

  export let title: string = '';
  export let i18n: Record<string, string> = {};
  export let isPagedMode: boolean = false;
  export let isInspectorOpen: boolean = false;
  export let isTocOpen: boolean = false;
  export let activeDrawerTab: 'kb' | 'comments' = 'kb';

  export let entityCount: number = 0;
  export let commentCount: number = 0;
  export let componentCount: number = 0;
  export let educativeMode: boolean = true;
  export let hasSourceMarkdown: boolean = false;
  export let onTogglePaged: (() => void) | undefined = undefined;

  const dispatch = createEventDispatcher();
  let progress: number = 0;
  let activeSection: string = '';
  let isDarkMode: boolean = true;
  let isMoreMenuOpen: boolean = false;

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
    isMoreMenuOpen = false;
    window.print();
  }

  function togglePaged() {
    if (onTogglePaged) onTogglePaged();
    dispatch('togglePaged');
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function handleEducativeToggle() {
    isMoreMenuOpen = false;
    dispatch('toggleEducativeMode');
  }

  function handleDownloadSource() {
    isMoreMenuOpen = false;
    dispatch('downloadSource');
  }

  function handleWindowClick(e: MouseEvent) {
    if (isMoreMenuOpen) {
      const target = e.target as HTMLElement;
      if (!target.closest('.more-actions-container')) {
        isMoreMenuOpen = false;
      }
    }
  }

  onMount(() => {
    // Initial theme detection
    const currentTheme = document.documentElement.getAttribute('data-theme') || document.documentElement.dataset.theme;
    if (currentTheme) {
      isDarkMode = currentTheme === 'dark';
    } else {
      const isCyber = document.body.classList.contains('theme-forensic-cyber');
      const hasDarkClass = document.body.classList.contains('dark-theme');
      isDarkMode = isCyber || hasDarkClass;
      document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    }

    window.addEventListener('scroll', updateScrollState, { passive: true });
    window.addEventListener('click', handleWindowClick);
    updateScrollState();
    return () => {
      window.removeEventListener('scroll', updateScrollState);
      window.removeEventListener('click', handleWindowClick);
    };
  });
</script>

<aside id="viewer-hud-ribbon" class="hud-container" aria-label="Document HUD">
  <div class="progress-bar-track">
    <div class="progress-bar-fill" style="width: {progress}%;"></div>
  </div>
  <div class="hud-content">
    <div class="hud-left">
      <!-- ToC Toggle Button -->
      <button
        class="action-btn icon-only-btn toc-btn"
        class:active={isTocOpen}
        on:click={() => dispatch('toggleToc')}
        title={i18n['ui.toggle_toc'] || 'Toggle Table of Contents (T)'}
        aria-label="Toggle Table of Contents"
      >
        <Icon name="menu" size={15} />
      </button>

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
      {#if componentCount > 0}
        <span class="hud-pill hud-pill-component" title="Document contains {componentCount} interactive Svelte component(s)">
          <Icon name="zap" size={13} />
          <span>Interactive ({componentCount})</span>
        </span>
      {/if}

      <!-- Entity Drawer Badge Button -->
      <button
        class="action-btn pill-btn"
        class:active={isInspectorOpen && activeDrawerTab === 'kb'}
        on:click={() => dispatch('toggleInspector', 'kb')}
        title={entityCount > 0 ? `${i18n['ui.all_entities'] || 'Entities'} (${entityCount})` : (i18n['ui.all_entities'] || 'Entities')}
      >
        <Icon name="tag" size={13} />
        <span class="badge-label">{i18n['ui.all_entities'] || 'Entities'}</span>
        {#if entityCount > 0}
          <span class="badge-count">{entityCount}</span>
        {/if}
      </button>

      <!-- Review Notes Drawer Badge Button -->
      <button
        class="action-btn pill-btn"
        class:active={isInspectorOpen && activeDrawerTab === 'comments'}
        on:click={() => dispatch('toggleInspector', 'comments')}
        title={commentCount > 0 ? `Review Notes (${commentCount})` : 'Review Notes'}
      >
        <Icon name="message-square" size={13} />
        <span class="sr-only">💬</span>
        <span class="badge-label">Notes</span>
        {#if commentCount > 0}
          <span class="badge-count">{commentCount}</span>
        {/if}
      </button>

      <!-- Segmented View Mode Toggle: [ Web | Paper ] -->
      <div class="segmented-control" role="group" aria-label="Display Mode">
        <button
          class="segmented-item"
          class:is-active={!isPagedMode}
          on:click={() => isPagedMode && togglePaged()}
          title={i18n['ui.web_view'] || 'Web View'}
        >
          <Icon name="layout" size={12} />
          <span>Web</span>
        </button>
        <button
          class="segmented-item"
          class:is-active={isPagedMode}
          on:click={() => !isPagedMode && togglePaged()}
          title={i18n['ui.paper_view'] || 'Paper View'}
        >
          <Icon name="file-text" size={12} />
          <span>Paper</span>
        </button>
      </div>

      <!-- Theme Switcher (Icon-only) -->
      <button
        class="action-btn icon-only-btn theme-toggle-btn"
        on:click={toggleTheme}
        title={isDarkMode ? 'Switch to Light Theme' : 'Switch to Dark Theme'}
      >
        <Icon name={isDarkMode ? 'moon' : 'sun'} size={14} />
      </button>

      <!-- More Actions ("···" Popover Menu) -->
      <div class="more-actions-container">
        <button
          class="action-btn icon-only-btn more-btn"
          class:active={isMoreMenuOpen}
          on:click|stopPropagation={() => (isMoreMenuOpen = !isMoreMenuOpen)}
          title={i18n['ui.more_actions'] || 'More actions'}
          aria-expanded={isMoreMenuOpen}
        >
          <Icon name="more-horizontal" size={16} />
        </button>

        {#if isMoreMenuOpen}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div class="more-dropdown-menu" on:click|stopPropagation>
            <button class="dropdown-item" on:click={handleEducativeToggle}>
              <Icon name="academic" size={14} />
              <div class="dropdown-item-text">
                <span class="dropdown-label">{educativeMode ? (i18n['ui.educative_mode'] || 'Educative Mode') : (i18n['ui.reader_mode'] || 'Reader Mode')}</span>
                <span class="dropdown-hint">{educativeMode ? 'Annotations visible' : 'Clean reader focus'}</span>
              </div>
            </button>

            <button class="dropdown-item" on:click={handlePrint}>
              <Icon name="printer" size={14} />
              <div class="dropdown-item-text">
                <span class="dropdown-label">{i18n['ui.print'] || 'Print / Save as PDF'}</span>
                <span class="dropdown-hint">Native browser print</span>
              </div>
            </button>

            {#if hasSourceMarkdown}
              <button class="dropdown-item" on:click={handleDownloadSource}>
                <Icon name="download" size={14} />
                <div class="dropdown-item-text">
                  <span class="dropdown-label">{i18n['ui.source_markdown'] || 'Download Markdown (.md)'}</span>
                  <span class="dropdown-hint">Extract embedded original source</span>
                </div>
              </button>
            {/if}

            {#if componentCount > 0}
              <div class="dropdown-divider"></div>
              <div class="dropdown-info-item">
                <Icon name="zap" size={13} />
                <span>Interactive components ({componentCount})</span>
              </div>
            {/if}
          </div>
        {/if}
      </div>
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
    font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
    box-shadow: none;
  }
  .hud-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1rem;
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
    gap: 0.45rem;
    cursor: pointer;
    padding: 0;
    text-align: left;
    white-space: nowrap;
  }
  .hud-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #0284c7;
    box-shadow: none;
    flex-shrink: 0;
  }
  .hud-title {
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #f8fafc;
    text-transform: none;
    font-weight: 600;
  }
  .hud-sep {
    color: #64748b;
    font-size: 0.85rem;
    user-select: none;
  }
  .hud-active-section {
    font-size: 0.78rem;
    color: #94a3b8;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 320px;
  }
  .hud-right {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-shrink: 0;
  }

  .hud-pill {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    font-size: 0.72rem;
    font-weight: 600;
    user-select: none;
  }
  .hud-pill-component {
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid rgba(16, 185, 129, 0.4);
    color: #34d399;
  }
  :global([data-theme="light"]) .hud-pill-component,
  :global(body.light-theme) .hud-pill-component {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: #059669;
  }

  .action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.14);
    color: #f1f5f9;
    padding: 0.22rem 0.6rem;
    border-radius: 4px;
    font-size: 0.74rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s, border-color 0.15s, color 0.15s;
    user-select: none;
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

  .icon-only-btn {
    padding: 0.25rem 0.45rem;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .toc-btn {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
  }

  .pill-btn {
    border-radius: 9999px;
    padding: 0.18rem 0.55rem;
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

  .badge-label {
    font-size: 0.72rem;
  }

  .badge-count {
    background: rgba(56, 189, 248, 0.25);
    color: #38bdf8;
    border-radius: 9999px;
    padding: 0.05rem 0.35rem;
    font-size: 0.68rem;
    font-weight: 700;
    margin-left: 0.1rem;
  }

  /* Segmented View Mode Toggle */
  .segmented-control {
    display: inline-flex;
    align-items: center;
    background: rgba(0, 0, 0, 0.28);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    padding: 2px;
    gap: 2px;
  }
  .segmented-item {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: transparent;
    border: none;
    color: #94a3b8;
    padding: 0.18rem 0.5rem;
    border-radius: 3px;
    font-size: 0.72rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.12s ease;
  }
  .segmented-item:hover {
    color: #f8fafc;
  }
  .segmented-item.is-active {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.25);
  }

  /* More Actions Popover */
  .more-actions-container {
    position: relative;
    display: inline-flex;
  }
  .more-dropdown-menu {
    position: absolute;
    top: calc(100% + 8px);
    right: 0;
    width: 250px;
    background: rgba(15, 23, 42, 0.96);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.4);
    padding: 0.4rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    z-index: 10001;
    animation: menuFadeIn 0.15s ease-out;
  }

  @keyframes menuFadeIn {
    from {
      opacity: 0;
      transform: translateY(-6px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }

  .dropdown-item {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    background: transparent;
    border: none;
    color: #cbd5e1;
    padding: 0.5rem 0.65rem;
    border-radius: 5px;
    text-align: left;
    cursor: pointer;
    transition: background 0.12s, color 0.12s;
    width: 100%;
    box-sizing: border-box;
  }
  .dropdown-item:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
  }
  .dropdown-item-text {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    overflow: hidden;
  }
  .dropdown-label {
    font-size: 0.78rem;
    font-weight: 600;
  }
  .dropdown-hint {
    font-size: 0.68rem;
    color: #64748b;
  }
  .dropdown-divider {
    height: 1px;
    background: rgba(255, 255, 255, 0.08);
    margin: 0.25rem 0;
  }
  .dropdown-info-item {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.35rem 0.65rem;
    font-size: 0.7rem;
    color: #34d399;
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
    background: #0284c7;
    transition: width 0.05s linear;
  }

  /* Light Theme overrides */
  :global([data-theme="light"]) .hud-container,
  :global(body.light-theme) .hud-container {
    background: rgba(255, 255, 255, 0.88);
    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.02);
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
  :global([data-theme="light"]) .badge-count,
  :global(body.light-theme) .badge-count {
    background: rgba(2, 132, 199, 0.15);
    color: #0284c7;
  }
  :global([data-theme="light"]) .segmented-control,
  :global(body.light-theme) .segmented-control {
    background: rgba(0, 0, 0, 0.06);
    border-color: rgba(0, 0, 0, 0.1);
  }
  :global([data-theme="light"]) .segmented-item,
  :global(body.light-theme) .segmented-item {
    color: #64748b;
  }
  :global([data-theme="light"]) .segmented-item:hover,
  :global(body.light-theme) .segmented-item:hover {
    color: #0f172a;
  }
  :global([data-theme="light"]) .segmented-item.is-active,
  :global(body.light-theme) .segmented-item.is-active {
    background: #ffffff;
    color: #0f172a;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }
  :global([data-theme="light"]) .more-dropdown-menu,
  :global(body.light-theme) .more-dropdown-menu {
    background: rgba(255, 255, 255, 0.98);
    border-color: rgba(0, 0, 0, 0.1);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.12);
  }
  :global([data-theme="light"]) .dropdown-item,
  :global(body.light-theme) .dropdown-item {
    color: #334155;
  }
  :global([data-theme="light"]) .dropdown-item:hover,
  :global(body.light-theme) .dropdown-item:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #0f172a;
  }
  :global([data-theme="light"]) .dropdown-hint,
  :global(body.light-theme) .dropdown-hint {
    color: #94a3b8;
  }
  :global([data-theme="light"]) .dropdown-divider,
  :global(body.light-theme) .dropdown-divider {
    background: rgba(0, 0, 0, 0.08);
  }

  @media (max-width: 768px) {
    .badge-label {
      display: none;
    }
    .hud-active-section {
      display: none;
    }
  }

  @media print {
    .hud-container {
      display: none !important;
    }
  }
</style>
