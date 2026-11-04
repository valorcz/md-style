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
  let selectedDepth: number = defaultDepth; // 2 = H1-H2, 3 = H1-H3, 6 = All
  let tocContainer: HTMLElement | null = null;
  let spineRight: number = 0;
  let isDockedSpine: boolean = false;

  function slugify(text: string): string {
    return text.toLowerCase().replace(/[^\w\s-]/g, '').trim().replace(/[\s_]+/g, '-');
  }

  function extractHeadings() {
    const selector = 'main h1, main h2, main h3, main h4, .report-content h1, .report-content h2, .report-content h3, .report-content h4, article h1, article h2, article h3, article h4';
    let nodes = Array.from(document.querySelectorAll(selector));

    if (nodes.length === 0) {
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

  function updateDocking() {
    const docEl = document.querySelector('.report-content') || document.querySelector('main') || document.body;
    if (!docEl) return;
    const docRect = docEl.getBoundingClientRect();

    // On screens >= 1100px with sufficient left margin, dock cleanly as a paper spine
    if (window.innerWidth >= 1100 && docRect.left >= 160) {
      isDockedSpine = true;
      spineRight = Math.max(16, window.innerWidth - docRect.left + 24);
    } else {
      isDockedSpine = false;
      spineRight = 0;
    }
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
      if (!isDockedSpine) {
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
    updateDocking();
    window.addEventListener('scroll', updateActiveHeading, { passive: true });
    window.addEventListener('resize', updateDocking);
    updateActiveHeading();

    return () => {
      window.removeEventListener('scroll', updateActiveHeading);
      window.removeEventListener('resize', updateDocking);
    };
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && !isDockedSpine}
  <!-- Backdrop for mobile/tablet overlay only -->
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div class="sidebar-toc-backdrop" on:click={onClose}></div>
{/if}

<aside
  class="sidebar-toc"
  class:is-open={isOpen}
  class:is-spine={isDockedSpine}
  style={isDockedSpine ? `right: ${spineRight}px;` : ''}
  bind:this={tocContainer}
  aria-label={i18n['ui.sidebar_toc'] || 'Table of Contents'}
  aria-hidden={!isOpen}
>
  <div class="toc-header">
    <div class="toc-title-row">
      <div class="toc-title-group">
        <Icon name="list" size={14} />
        <span class="toc-heading">{i18n['ui.sidebar_toc'] || 'Obsah'}</span>
      </div>
      <button class="toc-close-btn" on:click={onClose} title={i18n['ui.close'] || 'Close'}>
        <Icon name="x" size={14} />
      </button>
    </div>

    <!-- Depth filter switcher -->
    <div class="toc-depth-filter" role="radiogroup" aria-label="Heading Depth Filter">
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 2}
        on:click={() => (selectedDepth = 2)}
        title="Pouze H1–H2"
      >
        H2
      </button>
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 3}
        on:click={() => (selectedDepth = 3)}
        title="H1–H3"
      >
        H3
      </button>
      <button
        class="depth-pill"
        class:is-active={selectedDepth === 6}
        on:click={() => (selectedDepth = 6)}
        title="Vše"
      >
        Vše
      </button>
    </div>
  </div>

  <div class="toc-scroll-body">
    {#if filteredHeadings.length === 0}
      <div class="toc-empty">
        <span class="toc-empty-text">Žádné nadpisy nebyly nalezeny.</span>
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
  /* Base element */
  .sidebar-toc {
    display: flex;
    flex-direction: column;
    z-index: 9998;
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    transition: opacity 0.2s cubic-bezier(0.16, 1, 0.3, 1), transform 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }

  /* --------------------------------------------------------------------------
     DESKTOP SPINE MODE (sample.html style):
     - Placed on the LEFT side of the document (right: ${spineRight}px)
     - NO special box (transparent background, no borders, no box-shadow)
     - Text aligned to the RIGHT towards the document paper
     -------------------------------------------------------------------------- */
  @media (min-width: 1100px) {
    .sidebar-toc.is-spine {
      position: fixed;
      top: 5rem;
      bottom: 3rem;
      width: 200px;
      max-width: 220px;
      left: auto;
      background: transparent !important;
      border: none !important;
      box-shadow: none !important;
      backdrop-filter: none !important;
      -webkit-backdrop-filter: none !important;
      text-align: right;
      opacity: 0;
      pointer-events: none;
      transform: translateX(-8px);
    }

    .sidebar-toc.is-spine.is-open {
      opacity: 1;
      pointer-events: auto;
      transform: translateX(0);
    }

    .sidebar-toc.is-spine .toc-header {
      padding: 0 0.5rem 0.65rem 0;
      border: none;
      display: flex;
      flex-direction: column;
      align-items: flex-end;
      gap: 0.35rem;
    }

    .sidebar-toc.is-spine .toc-title-row {
      justify-content: flex-end;
      gap: 0.4rem;
    }

    .sidebar-toc.is-spine .toc-heading {
      font-size: 0.72rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.06em;
      color: #94a3b8;
    }

    .sidebar-toc.is-spine .toc-depth-filter {
      justify-content: flex-end;
      gap: 0.25rem;
    }

    .sidebar-toc.is-spine .depth-pill {
      background: transparent;
      border: 1px solid rgba(0, 0, 0, 0.08);
      color: #94a3b8;
      font-size: 0.65rem;
      padding: 0.08rem 0.35rem;
      border-radius: 4px;
      cursor: pointer;
    }

    .sidebar-toc.is-spine .depth-pill:hover {
      color: #0f172a;
      border-color: rgba(0, 0, 0, 0.2);
    }

    .sidebar-toc.is-spine .depth-pill.is-active {
      color: #0284c7;
      border-color: #0284c7;
      font-weight: 600;
    }

    /* Right-aligned spine navigation links */
    .sidebar-toc.is-spine .toc-list {
      list-style: none !important;
      padding: 0;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .sidebar-toc.is-spine .toc-item {
      list-style: none !important;
      margin: 0;
      padding: 0;
    }

    .sidebar-toc.is-spine .toc-link {
      display: block;
      text-align: right;
      text-decoration: none;
      font-size: 0.78rem;
      line-height: 1.42;
      color: #64748b;
      padding: 0.25rem 0.6rem 0.25rem 0;
      border-right: 2px solid transparent;
      border-left: none !important;
      background: transparent !important;
      transition: color 0.15s ease, border-color 0.15s ease;
      white-space: normal;
      word-break: break-word;
    }

    .sidebar-toc.is-spine .toc-link:hover {
      color: #0f172a;
    }

    .sidebar-toc.is-spine .toc-link.is-active {
      color: #0f172a;
      font-weight: 600;
      border-right-color: #0284c7;
    }

    /* Hierarchy indentation pushed to the left because text is right-aligned */
    .sidebar-toc.is-spine .toc-item.level-1 .toc-link {
      font-weight: 600;
      padding-right: 0.6rem;
    }
    .sidebar-toc.is-spine .toc-item.level-2 .toc-link {
      padding-right: 0.6rem;
    }
    .sidebar-toc.is-spine .toc-item.level-3 .toc-link {
      font-size: 0.74rem;
      opacity: 0.88;
      padding-right: 1.1rem;
    }
    .sidebar-toc.is-spine .toc-item.level-4 .toc-link {
      font-size: 0.7rem;
      opacity: 0.78;
      padding-right: 1.6rem;
    }

    /* Dark theme spine */
    :global([data-theme="dark"]) .sidebar-toc.is-spine .toc-heading {
      color: #64748b;
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .depth-pill {
      border-color: rgba(255, 255, 255, 0.1);
      color: #94a3b8;
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .depth-pill:hover {
      color: #f1f5f9;
      border-color: rgba(255, 255, 255, 0.25);
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .depth-pill.is-active {
      color: #38bdf8;
      border-color: #38bdf8;
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .toc-link {
      color: #94a3b8;
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .toc-link:hover {
      color: #f1f5f9;
    }
    :global([data-theme="dark"]) .sidebar-toc.is-spine .toc-link.is-active {
      color: #f8fafc;
      border-right-color: #38bdf8;
    }
  }

  /* --------------------------------------------------------------------------
     MOBILE & TABLET SLIDE-OUT DRAWER (< 1100px)
     -------------------------------------------------------------------------- */
  @media (max-width: 1099px) {
    .sidebar-toc {
      position: fixed;
      top: 40px;
      bottom: 0;
      left: 0;
      width: 270px;
      max-width: 85vw;
      background: rgba(255, 255, 255, 0.95);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border-right: 1px solid rgba(0, 0, 0, 0.08);
      box-shadow: 4px 0 24px rgba(0, 0, 0, 0.12);
      transform: translateX(-100%);
      text-align: left;
    }

    .sidebar-toc.is-open {
      transform: translateX(0);
    }

    .sidebar-toc-backdrop {
      position: fixed;
      top: 40px;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.2);
      z-index: 9997;
    }

    .toc-header {
      padding: 0.85rem 1rem 0.65rem 1rem;
      border-bottom: 1px solid rgba(0, 0, 0, 0.06);
    }

    .toc-title-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 0.5rem;
    }

    .toc-title-group {
      display: flex;
      align-items: center;
      gap: 0.4rem;
      font-weight: 600;
      font-size: 0.85rem;
      color: #0f172a;
    }

    .toc-close-btn {
      background: transparent;
      border: none;
      color: #64748b;
      cursor: pointer;
      padding: 0.2rem;
    }

    .toc-depth-filter {
      display: flex;
      gap: 0.35rem;
    }

    .depth-pill {
      background: rgba(0, 0, 0, 0.04);
      border: 1px solid rgba(0, 0, 0, 0.08);
      padding: 0.12rem 0.45rem;
      border-radius: 4px;
      font-size: 0.7rem;
      cursor: pointer;
      color: #475569;
    }

    .depth-pill.is-active {
      background: rgba(2, 132, 199, 0.1);
      border-color: #0284c7;
      color: #0284c7;
      font-weight: 600;
    }

    .toc-list {
      list-style: none;
      padding: 0.75rem 0.5rem;
      margin: 0;
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
    }

    .toc-item {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    .toc-item.level-1 { padding-left: 0.2rem; }
    .toc-item.level-2 { padding-left: 0.7rem; }
    .toc-item.level-3 { padding-left: 1.4rem; }
    .toc-item.level-4 { padding-left: 2.0rem; }

    .toc-link {
      display: block;
      color: #475569;
      text-decoration: none;
      padding: 0.32rem 0.55rem;
      border-radius: 4px;
      font-size: 0.8rem;
      line-height: 1.35;
      border-left: 2px solid transparent;
    }

    .toc-link:hover {
      background: rgba(0, 0, 0, 0.04);
      color: #0f172a;
    }

    .toc-link.is-active {
      background: rgba(2, 132, 199, 0.08);
      border-left-color: #0284c7;
      color: #0284c7;
      font-weight: 600;
    }

    :global([data-theme="dark"]) .sidebar-toc {
      background: rgba(18, 19, 22, 0.95);
      border-right-color: rgba(255, 255, 255, 0.08);
      color: #f1f5f9;
    }
    :global([data-theme="dark"]) .toc-title-group {
      color: #f8fafc;
    }
    :global([data-theme="dark"]) .toc-link {
      color: #94a3b8;
    }
    :global([data-theme="dark"]) .toc-link:hover {
      background: rgba(255, 255, 255, 0.06);
      color: #f8fafc;
    }
    :global([data-theme="dark"]) .toc-link.is-active {
      background: rgba(56, 189, 248, 0.12);
      border-left-color: #38bdf8;
      color: #38bdf8;
    }
  }

  .toc-scroll-body {
    flex: 1;
    overflow-y: auto;
    scrollbar-width: thin;
    scrollbar-color: rgba(0, 0, 0, 0.1) transparent;
  }

  :global([data-theme="dark"]) .toc-scroll-body {
    scrollbar-color: rgba(255, 255, 255, 0.1) transparent;
  }

  .toc-tree {
    display: flex;
    flex-direction: column;
  }

  .toc-empty {
    padding: 2rem 1rem;
    text-align: center;
    color: #94a3b8;
    font-size: 0.78rem;
  }

  @media print {
    .sidebar-toc, .sidebar-toc-backdrop {
      display: none !important;
    }
  }
</style>
