<script lang="ts">
  import Badge from './ui/Badge.svelte';
  import Button from './ui/Button.svelte';

  export let entity: any = null;
  export let position: { x: number; y: number } | null = null;
  export let isOpen: boolean = false;
  export let onOpenDetails: (entity: any) => void = () => {};
  export let onClose: () => void = () => {};

  let cardEl: HTMLElement | null = null;
  let topPx: number = 0;
  let leftPx: number = 0;
  let isFlipped: boolean = false;
  let arrowOffsetPx: number = 20;

  const cardWidth = 320;
  const cardHeight = 160;

  $: if (position && isOpen) {
    calculatePosition(position);
  }

  function calculatePosition(pos: { x: number; y: number }) {
    if (typeof window === 'undefined') return;

    let x = Math.min(window.innerWidth - cardWidth - 16, Math.max(16, pos.x - 20));
    let y = pos.y + 10;
    let flipped = false;

    // Flip upwards if overflows bottom of viewport
    if (y + cardHeight > window.innerHeight) {
      y = Math.max(16, pos.y - cardHeight - 20);
      flipped = true;
    }

    leftPx = x;
    topPx = y;
    isFlipped = flipped;
    arrowOffsetPx = Math.max(16, Math.min(pos.x - x + 12, cardWidth - 24));
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape' && isOpen) {
      onClose();
    }
  }

  function getBadgeLabel(ent: any): string {
    if (!ent) return '';
    const t = (ent.type || ent.category || '').toLowerCase();
    if (t === 'statute' || t === 'law') return 'Zákon / Norma';
    if (t === 'standard') return 'Standard';
    if (t === 'authority' || t === 'institution') return 'Instituce';
    if (t === 'ico' || t === 'company' || t === 'ares') return 'Subjekt';
    if (t === 'cve' || t === 'cwe' || t === 'vulnerability') return 'Zranitelnost';
    if (t === 'mitre') return 'Taktika / Technika';
    return ent.type || ent.category || 'Pojem';
  }

  function getSeverityColor(sev: string): string {
    const s = (sev || '').toUpperCase();
    if (s === 'CRITICAL') return '#dc2626';
    if (s === 'HIGH') return '#ea580c';
    if (s === 'MEDIUM') return '#b45309';
    return 'var(--color-accent, #2563eb)';
  }

  function getTitle(ent: any): string {
    if (!ent) return '';
    return ent.title || ent.name || ent.id || '';
  }

  function getSummary(ent: any): string {
    if (!ent) return '';
    const text = ent.summary || ent.description || ent.details || '';
    if (typeof text === 'string') {
      if (text.length > 170) {
        return text.slice(0, 167) + '...';
      }
      return text;
    }
    return '';
  }
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen && entity}
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="entity-hover-card"
    class:is-flipped={isFlipped}
    bind:this={cardEl}
    style="top: {topPx}px; left: {leftPx}px;"
    on:mouseenter
    on:mouseleave
  >
    <!-- Pointer Arrow / Notch -->
    <div
      class="hover-card-arrow"
      class:arrow-bottom={isFlipped}
      class:arrow-top={!isFlipped}
      style="left: {arrowOffsetPx}px;"
    ></div>

    <div class="card-header">
      <div class="card-badge-row">
        <Badge variant="subtle" color="var(--color-accent, #2563eb)" size="sm">
          {getBadgeLabel(entity)}
        </Badge>
        {#if entity.severity && entity.severity !== 'INFO'}
          <Badge variant="solid" color={getSeverityColor(entity.severity)} size="sm">
            {entity.severity}
          </Badge>
        {/if}
      </div>
      <code class="card-entity-id">{entity.id || ''}</code>
    </div>

    <div class="card-title">{getTitle(entity)}</div>

    {#if getSummary(entity)}
      <div class="card-summary">{getSummary(entity)}</div>
    {/if}

    <div class="card-footer">
      <Button
        class="card-action-btn"
        variant="ghost"
        size="sm"
        icon="arrow-right"
        iconRight={true}
        on:click={() => onOpenDetails(entity)}
        title="Otevřít podrobnosti v inspektoru"
      >
        <span>Podrobnosti</span>
      </Button>
    </div>
  </div>
{/if}

<style>
  .entity-hover-card {
    position: fixed;
    z-index: 10001;
    width: 320px;
    background: var(--color-paper, #ffffff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    padding: 0.9rem 1.05rem;
    box-shadow: 0 16px 36px -6px rgba(15, 23, 42, 0.16), 0 6px 16px -4px rgba(15, 23, 42, 0.08);
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    animation: cardPopIn 0.16s cubic-bezier(0.16, 1, 0.3, 1);
    pointer-events: auto;
    box-sizing: border-box;
  }

  @keyframes cardPopIn {
    from {
      opacity: 0;
      transform: translateY(5px) scale(0.97);
    }
    to {
      opacity: 1;
      transform: translateY(0) scale(1);
    }
  }

  /* Pointer Arrow */
  .hover-card-arrow {
    position: absolute;
    width: 10px;
    height: 10px;
    background: var(--color-paper, #ffffff);
    border-style: solid;
    border-color: var(--color-border, #e2e8f0);
    transform: rotate(45deg);
    pointer-events: none;
  }

  .hover-card-arrow.arrow-top {
    top: -6px;
    border-width: 1px 0 0 1px;
  }

  .hover-card-arrow.arrow-bottom {
    bottom: -6px;
    border-width: 0 1px 1px 0;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-bottom: 0.4rem;
  }

  .card-badge-row {
    display: flex;
    align-items: center;
    gap: 0.35rem;
    flex-wrap: wrap;
  }

  .card-entity-id {
    font-family: var(--font-mono, monospace);
    font-size: 0.7rem;
    color: var(--color-text-muted, #64748b);
    background: rgba(0, 0, 0, 0.04);
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
  }

  .card-title {
    font-size: 0.95rem;
    font-weight: 700;
    color: var(--color-primary, #0f172a);
    line-height: 1.35;
    margin-bottom: 0.4rem;
  }

  .card-summary {
    font-size: 0.79rem;
    line-height: 1.5;
    color: var(--color-text-muted, #475569);
    margin-bottom: 0.75rem;
  }

  .card-footer {
    display: flex;
    justify-content: flex-end;
    border-top: 1px solid var(--color-border, rgba(0, 0, 0, 0.06));
    padding-top: 0.5rem;
    margin-top: 0.2rem;
  }

  /* Dark Theme */
  :global([data-theme="dark"] .entity-hover-card) {
    background: #1e2024;
    border-color: #2e323b;
    box-shadow: 0 18px 44px rgba(0, 0, 0, 0.65);
  }
  :global([data-theme="dark"] .hover-card-arrow) {
    background: #1e2024;
    border-color: #2e323b;
  }
  :global([data-theme="dark"] .card-entity-id) {
    background: rgba(255, 255, 255, 0.06);
    color: #94a3b8;
  }
  :global([data-theme="dark"] .card-title) {
    color: #f1f5f9;
  }
  :global([data-theme="dark"] .card-summary) {
    color: #94a3b8;
  }
  :global([data-theme="dark"] .card-footer) {
    border-top-color: #262930;
  }
</style>
