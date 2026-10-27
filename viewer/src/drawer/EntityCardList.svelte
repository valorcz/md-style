<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let entities: any[] = [];
  export let totalCount: number = 0;

  const dispatch = createEventDispatcher<{
    select: any;
  }>();

  function handleKeydown(event: KeyboardEvent, item: any) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      dispatch('select', item);
    }
  }
</script>

{#if totalCount === 0}
  <div class="empty-kb-notice">
    <p>No knowledge base entities were identified in this document.</p>
  </div>
{:else}
  <div class="entity-cards-list">
    {#each entities as item}
      <div
        class="entity-item-card"
        on:click={() => dispatch('select', item)}
        on:keydown={(e) => handleKeydown(e, item)}
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
    {#if entities.length === 0}
      <div class="no-results-msg">No entities matching your query.</div>
    {/if}
  </div>
{/if}

<style>
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
    text-align: left;
  }
  .entity-item-card:hover,
  .entity-item-card:focus-visible {
    border-color: #38bdf8;
    background: #24344d;
    transform: translateY(-1px);
    outline: none;
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

  /* Light Theme */
  :global([data-theme="light"]) .entity-item-card,
  :global(body.light-theme) .entity-item-card {
    background: #f8fafc;
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .entity-item-card:hover,
  :global([data-theme="light"]) .entity-item-card:focus-visible,
  :global(body.light-theme) .entity-item-card:hover,
  :global(body.light-theme) .entity-item-card:focus-visible {
    background: #f1f5f9;
    border-color: #0284c7;
  }
  :global([data-theme="light"]) .item-title,
  :global(body.light-theme) .item-title {
    color: #0f172a;
  }
</style>
