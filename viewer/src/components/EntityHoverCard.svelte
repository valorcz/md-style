<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './Icon.svelte';

  export let entity: any = null;
  export let position: { x: number; y: number } | null = null;
  export let isOpen: boolean = false;
  export let onOpenDetails: (entity: any) => void = () => {};
  export let onClose: () => void = () => {};

  let cardEl: HTMLElement | null = null;
  let topPx: number = 0;
  let leftPx: number = 0;

  $: if (position && isOpen) {
    calculatePosition(position);
  }

  function calculatePosition(pos: { x: number; y: number }) {
    if (typeof window === 'undefined') return;
    const cardWidth = 300;
    const cardHeight = 150;

    let x = Math.min(window.innerWidth - cardWidth - 16, Math.max(16, pos.x - 20));
    let y = pos.y + 12;

    // Flip upwards if overflows bottom of viewport
    if (y + cardHeight > window.innerHeight) {
      y = Math.max(16, pos.y - cardHeight - 12);
    }

    leftPx = x;
    topPx = y;
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && isOpen) {
      onClose();
    }
  }

  function getBadgeLabel(ent: any): string {
    if (!ent) return '';
    return ent.type || ent.category || (ent.severity ? `Riziko: ${ent.severity}` : 'Entita báze znalostí');
  }

  function getTitle(ent: any): string {
    if (!ent) return '';
    return ent.title || ent.name || ent.id || '';
  }

  function getSummary(ent: any): string {
    if (!ent) return '';
    const text = ent.summary || ent.description || ent.details || '';
    if (text.length > 180) {
      return text.slice(0, 177) + '...';
    }
    return text;
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && entity}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="entity-hover-card"
    bind:this={cardEl}
    style="top: {topPx}px; left: {leftPx}px;"
    on:mouseenter
    on:mouseleave
  >
    <div class="card-badge">{getBadgeLabel(entity)}</div>
    <div class="card-title">{getTitle(entity)}</div>
    {#if getSummary(entity)}
      <div class="card-summary">{getSummary(entity)}</div>
    {/if}
    <div class="card-footer">
      <button
        type="button"
        class="card-action-btn"
        on:click={() => onOpenDetails(entity)}
      >
        <span>Podrobnosti</span>
        <Icon name="arrow-right" size={12} />
      </button>
    </div>
  </div>
{/if}

<style>
  .entity-hover-card {
    position: fixed;
    z-index: 10001;
    width: 300px;
    background: var(--color-paper, #ffffff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    padding: 0.85rem 1rem;
    box-shadow: 0 12px 32px -4px rgba(15, 23, 42, 0.12), 0 4px 12px -2px rgba(15, 23, 42, 0.06);
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    animation: cardPopIn 0.15s cubic-bezier(0.16, 1, 0.3, 1);
    pointer-events: auto;
  }

  @keyframes cardPopIn {
    from {
      opacity: 0;
      transform: translateY(4px) scale(0.98);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  .card-badge {
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-accent, #2563eb);
    margin-bottom: 0.25rem;
  }

  .card-title {
    font-size: 0.92rem;
    font-weight: 700;
    color: var(--color-primary, #0f172a);
    line-height: 1.3;
    margin-bottom: 0.35rem;
  }

  .card-summary {
    font-size: 0.78rem;
    line-height: 1.48;
    color: var(--color-text-muted, #64748b);
    margin-bottom: 0.6rem;
  }

  .card-footer {
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--color-border, rgba(0, 0, 0, 0.05));
    padding-top: 0.45rem;
    margin-top: 0.25rem;
  }

  .card-action-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    background: transparent;
    border: none;
    color: var(--color-accent, #2563eb);
    font-size: 0.75rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0.15rem 0.3rem;
    border-radius: 4px;
    transition: background 0.15s ease, color 0.15s ease;
  }

  .card-action-btn:hover {
    background: rgba(37, 99, 235, 0.08);
    color: var(--color-primary, #0f172a);
  }

  :global([data-theme="dark"]) .entity-hover-card {
    background: #1a1b1f;
    border-color: #2e323b;
    box-shadow: 0 16px 40px rgba(0, 0, 0, 0.6);
  }

  :global([data-theme="dark"]) .card-badge {
    color: #60a5fa;
  }

  :global([data-theme="dark"]) .card-title {
    color: #f1f5f9;
  }

  :global([data-theme="dark"]) .card-summary {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .card-footer {
    border-top-color: #262930;
  }

  :global([data-theme="dark"]) .card-action-btn {
    color: #60a5fa;
  }

  :global([data-theme="dark"]) .card-action-btn:hover {
    background: rgba(96, 165, 250, 0.12);
    color: #ffffff;
  }
</style>
