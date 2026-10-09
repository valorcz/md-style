<script lang="ts">
  export let entity: any = null;
  export let isOpen: boolean = false;
  export let i18n: Record<string, string> = {};
  export let allEntities: Record<string, any> = {};
  export let hasSourceMarkdown: boolean = false;
  export let onClose: () => void = () => {};
  export let onSelectEntity: (e: any) => void = () => {};
  export let onDownloadSource: () => void = () => {};

  let searchQuery: string = '';
  let selectedCategory: string = 'all';

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && isOpen) {
      onClose();
    }
  }

  function copyToClipboard(text: string) {
    navigator.clipboard?.writeText(text);
  }

  $: entityList = Object.values(allEntities || {});

  $: categories = (() => {
    const counts: Record<string, number> = {};
    for (const e of entityList) {
      const type = (e.type || 'entity').toLowerCase();
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  })();

  $: filteredEntities = entityList.filter(e => {
    const q = searchQuery.toLowerCase().trim();
    const type = (e.type || 'entity').toLowerCase();
    const matchesCat = selectedCategory === 'all' || type === selectedCategory;
    if (!matchesCat) return false;
    if (!q) return true;
    return (
      (e.id || '').toLowerCase().includes(q) ||
      (e.title || '').toLowerCase().includes(q) ||
      (e.summary || '').toLowerCase().includes(q)
    );
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <div class="drawer-backdrop" on:click={onClose} role="presentation"></div>
  <aside class="drawer-container" aria-label="Entity Details Inspector">
    <!-- Header -->
    <header class="drawer-header">
      {#if entity}
        <button class="nav-back-btn" on:click={() => { entity = null; }}>
          ← {i18n.all_entities || 'All Entities'}
        </button>
        <div class="header-badges">
          <span class="badge badge-{entity.severity?.toLowerCase() || 'info'}">
            {entity.severity || 'INFO'}
          </span>
          {#if entity.badge}
            <span class="badge badge-meta">{entity.badge}</span>
          {/if}
        </div>
      {:else}
        <div class="header-title-block">
          <span class="header-icon">📦</span>
          <span class="header-title">{i18n.knowledge_inspector || 'Inspector & Knowledge Base'}</span>
        </div>
      {/if}
      <button class="close-btn" on:click={onClose} aria-label={i18n.close || 'Close'}>✕</button>
    </header>

    <div class="drawer-body">
      {#if entity}
        <!-- Single Entity Detail View -->
        <h2 class="entity-title">{entity.title || entity.label || entity.id}</h2>

        <div class="token-row">
          <code class="entity-id">{entity.id}</code>
          <button class="copy-btn" on:click={() => copyToClipboard(entity.id)} title={i18n.copy || 'Copy'}>
            📋 {i18n.copy || 'Copy'}
          </button>
        </div>

        {#if entity.summary}
          <div class="drawer-section">
            <h3>{i18n.summary || 'Summary'}</h3>
            <p class="summary-text">{entity.summary}</p>
          </div>
        {/if}

        {#if entity.attributes && Object.keys(entity.attributes).length > 0}
          <div class="drawer-section">
            <h3>{i18n.attributes || 'Attributes'}</h3>
            <table class="attributes-table">
              <tbody>
                {#each Object.entries(entity.attributes) as [key, val]}
                  <tr>
                    <th scope="row">{key}</th>
                    <td>{val}</td>
                  </tr>
                {/each}
              </tbody>
            </table>
          </div>
        {/if}

        {#if entity.references && entity.references.length > 0}
          <div class="drawer-section">
            <h3>{i18n.references || 'References'}</h3>
            <ul class="references-list">
              {#each entity.references as ref}
                <li>
                  <a href={ref.url} target="_blank" rel="noopener noreferrer">
                    {ref.title || ref.url} ↗
                  </a>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

        {#if entity.provenance}
          <footer class="drawer-footer">
            <small class="provenance-stamp">
              {i18n.provenance || 'Provenance'}: <strong>{entity.provenance.source}</strong> ·
              {i18n.status || 'Status'}: {entity.provenance.status}
              {#if entity.provenance.fetched_at}
                · {new Date(entity.provenance.fetched_at).toLocaleDateString()}
              {/if}
            </small>
          </footer>
        {/if}

      {:else}
        <!-- Catalog Browser View -->
        {#if hasSourceMarkdown}
          <div class="archive-action-card">
            <div class="archive-info">
              <span class="archive-icon">📄</span>
              <div class="archive-text">
                <strong>Source Document Archive</strong>
                <span>Embedded raw Markdown archive</span>
              </div>
            </div>
            <button class="download-archive-btn" on:click={onDownloadSource} title="Download Markdown Source">
              📥 Download .md
            </button>
          </div>
        {/if}

        {#if entityList.length > 0}
          <!-- Search & Filter Controls -->
          <div class="search-box">
            <input
              type="text"
              class="search-input"
              placeholder={i18n.filter_placeholder || 'Search knowledge entities...'}
              bind:value={searchQuery}
            />
            {#if searchQuery}
              <button class="search-clear-btn" on:click={() => (searchQuery = '')}>✕</button>
            {/if}
          </div>

          <!-- Category Pills -->
          <div class="category-pills">
            <button
              class="pill-btn"
              class:active={selectedCategory === 'all'}
              on:click={() => (selectedCategory = 'all')}
            >
              All ({entityList.length})
            </button>
            {#each Object.entries(categories) as [cat, count]}
              <button
                class="pill-btn"
                class:active={selectedCategory === cat}
                on:click={() => (selectedCategory = cat)}
              >
                {cat.toUpperCase()} ({count})
              </button>
            {/each}
          </div>

          <!-- Entity List -->
          <div class="entity-cards-list">
            {#each filteredEntities as item}
              <div
                class="entity-item-card"
                on:click={() => { entity = item; onSelectEntity(item); }}
                role="button"
                tabindex="0"
              >
                <div class="item-header">
                  <span class="item-id">{item.id}</span>
                  <span class="badge badge-{item.severity?.toLowerCase() || 'info'}">
                    {item.severity || 'INFO'}
                  </span>
                </div>
                {#if item.title && item.title !== item.id}
                  <div class="item-title">{item.title}</div>
                {/if}
                {#if item.summary}
                  <div class="item-summary">{item.summary}</div>
                {/if}
              </div>
            {/each}
            {#if filteredEntities.length === 0}
              <div class="no-results-msg">No entities matching your query.</div>
            {/if}
          </div>
        {:else}
          <div class="empty-kb-notice">
            <p>No knowledge base entities were identified in this document.</p>
          </div>
        {/if}
      {/if}
    </div>
  </aside>
{/if}

<style>
  .drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.55);
    backdrop-filter: blur(3px);
    z-index: 9998;
  }
  .drawer-container {
    position: fixed;
    top: 0;
    right: 0;
    bottom: 0;
    width: 460px;
    max-width: 92vw;
    background: #0b1120;
    color: #e2e8f0;
    border-left: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: -10px 0 30px rgba(0, 0, 0, 0.5);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    animation: slideIn 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.9rem 1.25rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: #0f172a;
  }
  .header-title-block {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .header-icon {
    font-size: 1.1rem;
  }
  .header-title {
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #f8fafc;
  }
  .nav-back-btn {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #cbd5e1;
    font-size: 0.8rem;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .nav-back-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
  .header-badges {
    display: flex;
    gap: 0.5rem;
    align-items: center;
  }
  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge-critical { background: #ef4444; color: #fff; }
  .badge-high { background: #f97316; color: #fff; }
  .badge-medium { background: #eab308; color: #000; }
  .badge-info { background: #3b82f6; color: #fff; }
  .badge-meta {
    background: rgba(255, 255, 255, 0.1);
    color: #94a3b8;
  }
  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
  .drawer-body {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    flex: 1;
  }
  .archive-action-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 0.85rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }
  .archive-info {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .archive-icon {
    font-size: 1.3rem;
  }
  .archive-text {
    display: flex;
    flex-direction: column;
    font-size: 0.82rem;
  }
  .archive-text strong {
    color: #f1f5f9;
  }
  .archive-text span {
    color: #94a3b8;
    font-size: 0.75rem;
  }
  .download-archive-btn {
    background: #0284c7;
    color: #ffffff;
    border: none;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s ease;
  }
  .download-archive-btn:hover {
    background: #0369a1;
  }
  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-input {
    width: 100%;
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    color: #f8fafc;
    padding: 0.5rem 0.75rem;
    font-size: 0.85rem;
    outline: none;
  }
  .search-input:focus {
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
  }
  .search-clear-btn {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    font-size: 0.85rem;
  }
  .category-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .pill-btn {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .pill-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
  }
  .pill-btn.active {
    background: #0284c7;
    border-color: #0284c7;
    color: #ffffff;
  }
  .entity-cards-list {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    overflow-y: auto;
  }
  .entity-item-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .entity-item-card:hover {
    border-color: #38bdf8;
    background: #24344d;
    transform: translateY(-1px);
  }
  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.3rem;
  }
  .item-id {
    font-family: monospace;
    font-size: 0.82rem;
    color: #38bdf8;
    font-weight: 600;
  }
  .item-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
  }
  .item-summary {
    font-size: 0.78rem;
    color: #94a3b8;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .no-results-msg, .empty-kb-notice {
    font-size: 0.85rem;
    color: #64748b;
    text-align: center;
    padding: 1.5rem 0;
  }
  .entity-title {
    font-size: 1.25rem;
    font-weight: 600;
    margin: 0;
    line-height: 1.3;
    color: #f8fafc;
  }
  .token-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .entity-id {
    font-family: monospace;
    font-size: 0.85rem;
    background: rgba(255, 255, 255, 0.06);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    color: #38bdf8;
  }
  .copy-btn {
    font-size: 0.75rem;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #cbd5e1;
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    cursor: pointer;
  }
  .copy-btn:hover {
    background: rgba(255, 255, 255, 0.1);
  }
  .drawer-section h3 {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin: 0 0 0.5rem 0;
  }
  .summary-text {
    font-size: 0.9rem;
    line-height: 1.5;
    margin: 0;
    color: #cbd5e1;
  }
  .attributes-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.85rem;
  }
  .attributes-table th, .attributes-table td {
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    text-align: left;
  }
  .attributes-table th {
    color: #94a3b8;
    width: 35%;
  }
  .attributes-table td {
    color: #cbd5e1;
  }
  .references-list {
    margin: 0;
    padding-left: 1.25rem;
    font-size: 0.85rem;
  }
  .references-list a {
    color: #38bdf8;
    text-decoration: none;
  }
  .references-list a:hover {
    text-decoration: underline;
  }
  .drawer-footer {
    margin-top: auto;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
  .provenance-stamp {
    font-size: 0.72rem;
    color: #64748b;
  }
</style>
