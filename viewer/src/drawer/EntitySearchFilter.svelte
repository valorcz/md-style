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
    background: var(--color-bg-alt, #f8fafc);
    border: 1px solid var(--color-border, #e2e8f0);
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
    color: var(--color-text-muted, #64748b);
  }
  .archive-text {
    display: flex;
    flex-direction: column;
    font-size: 0.82rem;
  }
  .archive-text strong {
    color: var(--color-text, #0f172a);
    font-weight: 600;
  }
  .archive-text span {
    color: var(--color-text-muted, #64748b);
    font-size: 0.75rem;
  }
  .download-archive-btn {
    background: var(--color-primary, #2563eb);
    color: #ffffff;
    border: none;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 0.35rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
  }
  .download-archive-btn:hover {
    opacity: 0.9;
  }
  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-icon {
    position: absolute;
    left: 10px;
    color: var(--color-text-muted, #94a3b8);
    display: flex;
    align-items: center;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    background: var(--color-paper, #ffffff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    color: var(--color-text, #0f172a);
    padding: 0.5rem 0.75rem 0.5rem 2.1rem;
    font-size: 0.85rem;
    outline: none;
    font-family: inherit;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .search-input:focus {
    border-color: var(--color-primary, #2563eb);
    box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.12);
  }
  .search-clear-btn {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: var(--color-text-muted, #94a3b8);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 4px;
  }
  .search-clear-btn:hover {
    color: var(--color-text, #0f172a);
    background: rgba(0, 0, 0, 0.05);
  }
  .category-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .pill-btn {
    background: var(--color-bg-alt, #f8fafc);
    border: 1px solid var(--color-border, #e2e8f0);
    color: var(--color-text-muted, #64748b);
    font-size: 0.75rem;
    font-weight: 500;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    cursor: pointer;
    transition: all 0.15s ease;
    font-family: inherit;
  }
  .pill-btn:hover {
    background: rgba(0, 0, 0, 0.04);
    color: var(--color-text, #0f172a);
  }
  .pill-btn.active {
    background: var(--color-text, #0f172a);
    border-color: var(--color-text, #0f172a);
    color: #ffffff;
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .archive-action-card {
    background: #1e293b;
    border-color: rgba(255, 255, 255, 0.1);
  }
  :global([data-theme="dark"]) .archive-text strong {
    color: #f1f5f9;
  }
  :global([data-theme="dark"]) .archive-text span {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .search-input {
    background: #1e293b;
    border-color: rgba(255, 255, 255, 0.12);
    color: #f8fafc;
  }
  :global([data-theme="dark"]) .search-clear-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.1);
  }
  :global([data-theme="dark"]) .pill-btn {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.1);
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .pill-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }
  :global([data-theme="dark"]) .pill-btn.active {
    background: var(--color-primary, #38bdf8);
    border-color: var(--color-primary, #38bdf8);
    color: #0f172a;
  }
</style>
