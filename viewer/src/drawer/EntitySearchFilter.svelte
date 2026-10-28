<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';

  export let searchQuery: string = '';
  export let selectedCategory: string = 'all';
  export let categories: Record<string, number> = {};
  export let entityCount: number = 0;
  export let hasSourceMarkdown: boolean = false;
  export let i18n: Record<string, string> = {};

  const dispatch = createEventDispatcher<{
    downloadSource: void;
  }>();
</script>

{#if hasSourceMarkdown}
  <div class="archive-action-card">
    <div class="archive-info">
      <span class="archive-icon"><Icon name="file-text" size={18} /></span>
      <div class="archive-text">
        <strong>Source Document Archive</strong>
        <span>Embedded raw Markdown archive</span>
      </div>
    </div>
    <button class="download-archive-btn" on:click={() => dispatch('downloadSource')} title="Download Markdown Source">
      <Icon name="file-text" size={13} />
      <span>Download .md</span>
    </button>
  </div>
{/if}

<div class="search-box">
  <span class="search-icon"><Icon name="search" size={13} /></span>
  <input
    type="text"
    class="search-input"
    placeholder={i18n.filter_placeholder || 'Search knowledge entities...'}
    bind:value={searchQuery}
  />
  {#if searchQuery}
    <button class="search-clear-btn" on:click={() => (searchQuery = '')} aria-label="Clear search">
      <Icon name="x" size={12} />
    </button>
  {/if}
</div>

<div class="category-pills">
  <button
    class="pill-btn"
    class:active={selectedCategory === 'all'}
    on:click={() => (selectedCategory = 'all')}
  >
    All ({entityCount})
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

<style>
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
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .download-archive-btn:hover {
    background: #0369a1;
  }
  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-icon {
    position: absolute;
    left: 10px;
    color: #64748b;
    display: flex;
    align-items: center;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    color: #f8fafc;
    padding: 0.5rem 0.75rem 0.5rem 2.1rem;
    font-size: 0.85rem;
    outline: none;
    font-family: inherit;
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
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 4px;
  }
  .search-clear-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.1);
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
    font-family: inherit;
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

  /* Light Theme */
  :global([data-theme="light"]) .archive-action-card,
  :global(body.light-theme) .archive-action-card {
    background: #f8fafc;
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .search-input,
  :global(body.light-theme) .search-input {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.15);
    color: #0f172a;
  }
  :global([data-theme="light"]) .pill-btn,
  :global(body.light-theme) .pill-btn {
    background: rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(0, 0, 0, 0.1);
    color: #475569;
  }
  :global([data-theme="light"]) .pill-btn:hover,
  :global(body.light-theme) .pill-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #0f172a;
  }
  :global([data-theme="light"]) .pill-btn.active,
  :global(body.light-theme) .pill-btn.active {
    background: #0284c7;
    color: #ffffff;
  }
</style>
