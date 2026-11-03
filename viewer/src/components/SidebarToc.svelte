<script lang="ts">
  import { onMount, tick } from 'svelte';
  import Icon from './Icon.svelte';

  export let isOpen: boolean = false;
  export let i18n: Record<string, string> = {};
  export let onClose: () => void = () => {};
  export let defaultDepth: number = 3;

  interface TocItem {
    id: string;
    title: string;
    level: number;
  }

  let headings: TocItem[] = [];
  let activeId: string = '';
  let selectedDepth: number = defaultDepth; // 2 = H1-H2, 3 = H1-H3, 4 = All
  let tocContainer: HTMLElement | null = null;

  function slugify(text: string): string {
    return text.toLowerCase().replace(/[^\w\s-]/g, '').trim().replace(/[\s_]+/g, '-');
  }

  function extractHeadings() {
    const selector = 'main h1, main h2, main h3, main h4, .report-content h1, .report-content h2, .report-content h3, .report-content h4, article h1, article h2, article h3, article h4';
    let nodes = Array.from(document.querySelectorAll(selector));

    if (nodes.length === 0) {
      // Fallback: query all headings outside hud and drawers
      nodes = Array.from(document.querySelectorAll('h1, h2, h3, h4')).filter(el => {
        return !el.closest('#viewer-hud-ribbon') && !el.closest('.drawer-container') && !el.closest('.sidebar-toc');
      });
    }

    const items: TocItem[] = [];
    nodes.forEach((el, idx) => {
      let id = el.id;
      const text = el.textContent?.trim() || '';
      if (!text) return;

      if (!id) {
        id = slugify(text) || `heading-${idx + 1}`;
        el.id = id;
      }

      const tag = el.tagName.toLowerCase();
      const level = parseInt(tag.replace('h', ''), 10) || 2;
      items.push({ id, title: text, level });
    });

    headings = items;
  }

  function updateActiveHeading() {
    if (headings.length === 0) return;
    const scrollPos = window.scrollY + 120;

    let current = '';
    for (const item of headings) {
      const el = document.getElementById(item.id);
      if (el) {
        const top = el.getBoundingClientRect().top + window.scrollY;
        if (top <= scrollPos) {
          current = item.id;
        } else {
          break;
        }
      }
    }

    if (current && current !== activeId) {
      activeId = current;
      tick().then(() => {
        const activeLink = tocContainer?.querySelector(`.toc-link[data-id="${activeId}"]`);
        if (activeLink) {
          activeLink.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      });
    }
  }

  function scrollToSection(id: string, e: MouseEvent) {
    e.preventDefault();
    const target = document.getElementById(id);
    if (target) {
      target.scrollIntoView({ behavior: 'smooth', block: 'start' });
      activeId = id;
      // On narrow screens (mobile/tablet), collapse on click
      if (window.innerWidth < 1024) {
        onClose();
      }
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && isOpen) {
      onClose();
    }
  }

  $: filteredHeadings = headings.filter(h => h.level <= selectedDepth);

  onMount(() => {
    extractHeadings();
    window.addEventListener('scroll', updateActiveHeading, { passive: true });
    updateActiveHeading();

    return () => {
      window.removeEventListener('scroll', updateActiveHeading);
    };
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <!-- Backdrop for mobile viewports -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="sidebar-toc-backdrop" on:click={onClose}></div>
{/if}

<aside
  class="sidebar-toc"
  class:is-open={isOpen}
  bind:this={tocContainer}
  aria-label={i18n['ui.sidebar_toc'] || 'Table of Contents'}
  aria-hidden={!isOpen}
>
  <div class="toc-header">
    <div class="toc-title-row">
      <div class="toc-title-group">
        <Icon name="list" size={16} />
        <span class="toc-heading">{i18n['ui.sidebar_toc'] || 'Table of Contents'}</span>
      </div>
      <button class="toc-close-btn" on:click={onClose} title={i18n['ui.close'] || 'Close'}>
        <Icon name="x" size={15} />
      </button>
    </div>

    <!-- Depth filter switcher -->
    <div class="toc-depth-filter" role="radiogroup" aria-label="Heading Depth Filter">
      <span class="depth-label">{i18n['ui.depth'] || 'Depth:'}</span>
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 2}
        on:click={() => (selectedDepth = 2)}
        title="Show H1–H2 headings"
      >
        H2
      </button>
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 3}
        on:click={() => (selectedDepth = 3)}
        title="Show H1–H3 headings"
      >
        H3
      </button>
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 6}
        on:click={() => (selectedDepth = 6)}
        title="Show all headings"
      >
        All
      </button>
    </div>
  </div>

  <div class="toc-scroll-body">
    {#if filteredHeadings.length === 0}
      <div class="toc-empty">
        <span class="toc-empty-text">No section headings found.</span>
      </div>
    {:else}
      <nav class="toc-tree">
        <ul class="toc-list">
          {#each filteredHeadings as item (item.id)}
            <li class="toc-item level-{item.level}">
              <a
                href="#{item.id}"
                class="toc-link"
                class:is-active={activeId === item.id}
                data-id={item.id}
                on:click={(e) => scrollToSection(item.id, e)}
              >
                <span class="toc-item-text">{item.title}</span>
              </a>
            </li>
          {/each}
        </ul>
      </nav>
    {/if}
  </div>
</aside>

<style>
  .sidebar-toc {
    position: fixed;
    top: 40px;
    bottom: 0;
    left: 0;
    width: 280px;
    max-width: 85vw;
    z-index: 9998;
    background: rgba(15, 23, 42, 0.94);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 4px 0 20px rgba(0, 0, 0, 0.25);
    display: flex;
    flex-direction: column;
    transform: translateX(-100%);
    transition: transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    font-family: var(--font-ui, var(--font-body, system-ui, sans-serif));
    color: #f1f5f9;
  }

  .sidebar-toc.is-open {
    transform: translateX(0);
  }

  /* Non-modal transparent dismiss layer for mobile only - NO BLUR */
  .sidebar-toc-backdrop {
    position: fixed;
    top: 40px;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.25);
    z-index: 9997;
    animation: fadeIn 0.15s ease-out;
  }

  @media (min-width: 1024px) {
    /* On desktop, ToC is docked alongside document: NO backdrop at all */
    .sidebar-toc-backdrop {
      display: none !important;
    }
    .sidebar-toc {
      box-shadow: 2px 0 12px rgba(0, 0, 0, 0.12);
    }
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .toc-header {
    padding: 0.85rem 1rem 0.65rem 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.07);
    flex-shrink: 0;
  }

  .toc-title-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.5rem;
  }

  .toc-title-group {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    color: #38bdf8;
    color: var(--accent-color, #38bdf8);
  }

  .toc-heading {
    font-size: 0.82rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #f8fafc;
  }

  .toc-close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 0.2rem;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.15s, background 0.15s;
  }

  .toc-close-btn:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.1);
  }

  .toc-depth-filter {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.72rem;
    color: #94a3b8;
  }

  .depth-label {
    margin-right: 0.2rem;
    font-weight: 500;
  }

  .depth-pill {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #cbd5e1;
    padding: 0.12rem 0.45rem;
    border-radius: 9999px;
    font-size: 0.7rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }

  .depth-pill:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }

  .depth-pill.is-active {
    background: rgba(56, 189, 248, 0.2);
    border-color: #38bdf8;
    color: #38bdf8;
    color: var(--accent-color, #38bdf8);
  }

  .toc-scroll-body {
    flex: 1;
    overflow-y: auto;
    padding: 0.75rem 0.5rem 1.5rem 0.5rem;
    scrollbar-width: thin;
    scrollbar-color: rgba(255, 255, 255, 0.2) transparent;
  }

  .toc-tree {
    display: flex;
    flex-direction: column;
  }

  .toc-list {
    list-style: none !important;
    list-style-type: none !important;
    margin: 0 !important;
    padding: 0 !important;
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .toc-item {
    margin: 0 !important;
    padding: 0 !important;
    list-style: none !important;
    list-style-type: none !important;
  }

  /* Force disable any theme-injected bullet points or pseudo-elements */
  :global(.sidebar-toc ul),
  :global(.sidebar-toc li),
  .toc-list,
  .toc-item {
    list-style: none !important;
    list-style-type: none !important;
  }

  :global(.sidebar-toc li::before),
  :global(.sidebar-toc li::after),
  :global(.sidebar-toc .toc-item::before),
  :global(.sidebar-toc .toc-item::after) {
    content: none !important;
    display: none !important;
  }

  :global(.sidebar-toc li::marker),
  :global(.sidebar-toc .toc-item::marker) {
    display: none !important;
    content: "" !important;
  }

  .toc-item.level-1 { padding-left: 0.4rem; font-weight: 600; }
  .toc-item.level-2 { padding-left: 0.8rem; font-weight: 500; }
  .toc-item.level-3 { padding-left: 1.5rem; font-weight: 400; font-size: 0.78rem; }
  .toc-item.level-4 { padding-left: 2.1rem; font-weight: 400; font-size: 0.74rem; opacity: 0.85; }

  .toc-link {
    display: block;
    color: #cbd5e1;
    text-decoration: none;
    padding: 0.32rem 0.55rem;
    border-radius: 4px;
    font-size: 0.8rem;
    line-height: 1.35;
    transition: background 0.12s ease, color 0.12s ease;
    border-left: 2px solid transparent;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .toc-link:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #f8fafc;
  }

  .toc-link.is-active {
    background: rgba(56, 189, 248, 0.14);
    border-left-color: #38bdf8;
    border-left-color: var(--accent-color, #38bdf8);
    color: #38bdf8;
    color: var(--accent-color, #38bdf8);
    font-weight: 600;
  }

  .toc-empty {
    padding: 2rem 1rem;
    text-align: center;
    color: #64748b;
    font-size: 0.8rem;
  }

  /* Light Theme overrides */
  :global([data-theme="light"]) .sidebar-toc,
  :global(body.light-theme) .sidebar-toc {
    background: rgba(255, 255, 255, 0.94);
    border-right-color: rgba(0, 0, 0, 0.08);
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.08);
    color: #1e293b;
  }

  :global([data-theme="light"]) .toc-heading,
  :global(body.light-theme) .toc-heading {
    color: #0f172a;
  }

  :global([data-theme="light"]) .toc-header,
  :global(body.light-theme) .toc-header {
    border-bottom-color: rgba(0, 0, 0, 0.07);
  }

  :global([data-theme="light"]) .depth-pill,
  :global(body.light-theme) .depth-pill {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.1);
    color: #475569;
  }

  :global([data-theme="light"]) .depth-pill.is-active,
  :global(body.light-theme) .depth-pill.is-active {
    background: rgba(2, 132, 199, 0.12);
    border-color: #0284c7;
    color: #0284c7;
  }

  :global([data-theme="light"]) .toc-link,
  :global(body.light-theme) .toc-link {
    color: #334155;
  }

  :global([data-theme="light"]) .toc-link:hover,
  :global(body.light-theme) .toc-link:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #0f172a;
  }

  :global([data-theme="light"]) .toc-link.is-active,
  :global(body.light-theme) .toc-link.is-active {
    background: rgba(2, 132, 199, 0.1);
    border-left-color: #0284c7;
    color: #0284c7;
  }

  @media print {
    .sidebar-toc, .sidebar-toc-backdrop {
      display: none !important;
    }
  }
</style>
