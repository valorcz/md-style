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
    gap: 0.5rem;
    overflow-y: auto;
  }
  .entity-item-card {
    background: var(--color-paper, #ffffff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
  }
  .entity-item-card:hover,
  .entity-item-card:focus-visible {
    border-color: var(--color-accent, #2563eb);
    background: rgba(37, 99, 235, 0.04);
    transform: translateY(-1px);
    outline: none;
  }
  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.25rem;
  }
  .item-id {
    font-family: inherit;
    font-size: 0.8rem;
    color: var(--color-accent, #2563eb);
    font-weight: 600;
  }
  .badge {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.12rem 0.4rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .badge-critical { background: rgba(239, 68, 68, 0.12); color: #dc2626; }
  .badge-high { background: rgba(249, 115, 22, 0.12); color: #ea580c; }
  .badge-medium { background: rgba(234, 179, 8, 0.14); color: #b45309; }
  .badge-info { background: rgba(37, 99, 235, 0.08); color: #2563eb; }
  .item-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--color-primary, #0f172a);
    margin-bottom: 0.2rem;
  }
  .item-summary {
    font-size: 0.76rem;
    color: var(--color-text-muted, #64748b);
    line-height: 1.45;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .no-results-msg, .empty-kb-notice {
    font-size: 0.82rem;
    color: var(--color-text-muted, #64748b);
    text-align: center;
    padding: 1.5rem 0;
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .entity-item-card {
    background: #23252a;
    border-color: #2e323b;
  }
  :global([data-theme="dark"]) .entity-item-card:hover,
  :global([data-theme="dark"]) .entity-item-card:focus-visible {
    background: #282b32;
    border-color: #60a5fa;
  }
  :global([data-theme="dark"]) .item-id {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .item-title {
    color: #f1f5f9;
  }
  :global([data-theme="dark"]) .item-summary {
    color: #94a3b8;
  }
</style>
