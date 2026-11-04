<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../Icon.svelte';

  export let relationships: Array<{ target: string; type?: string; relation?: string }> = [];
  export let title: string = 'Pivot Telemetry & Lateral Links';

  const dispatch = createEventDispatcher<{
    pivot: string;
  }>();

  function getTypeIcon(t: string | undefined): string {
    const type = (t || '').toLowerCase();
    if (type === 'cve') return 'alert-circle';
    if (type === 'cwe') return 'award';
    if (type === 'mitre') return 'alert-circle';
    if (type === 'winevent' || type === 'evtx') return 'file-text';
    if (type === 'ip') return 'layout';
    return 'box';
  }
</script>

{#if relationships && relationships.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name="layers" size={14} /></span>
      <span>{title}</span>
    </h3>
    <div class="relationship-chips">
      {#each relationships as rel}
        <button
          type="button"
          class="rel-chip type-{(rel.type || 'entity').toLowerCase()}"
          on:click={() => dispatch('pivot', rel.target)}
          title="Pivot to {rel.target}"
        >
          <span class="rel-icon"><Icon name={getTypeIcon(rel.type)} size={12} /></span>
          <span class="rel-badge">{rel.relation?.replace(/_/g, ' ') || 'relates to'}</span>
          <span class="rel-target">{rel.target} ↗</span>
        </button>
      {/each}
    </div>
  </div>
{/if}

<style>
  .drawer-section {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    margin-top: 0.5rem;
  }
  .section-heading {
    margin: 0;
    font-size: 0.74rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: var(--color-text-muted, #64748b);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .heading-icon {
    display: flex;
    align-items: center;
    color: var(--color-accent, #2563eb);
  }
  .relationship-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.35rem;
  }
  .rel-chip {
    background: rgba(37, 99, 235, 0.06);
    border: 1px solid rgba(37, 99, 235, 0.16);
    border-radius: 4px;
    padding: 0.25rem 0.5rem;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
  }
  .rel-chip:hover {
    background: rgba(37, 99, 235, 0.14);
    border-color: var(--color-accent, #2563eb);
  }
  .rel-icon {
    display: flex;
    align-items: center;
    color: var(--color-accent, #2563eb);
  }
  .rel-badge {
    font-size: 0.68rem;
    color: var(--color-text-muted, #64748b);
    text-transform: uppercase;
    font-weight: 500;
  }
  .rel-target {
    font-family: inherit;
    font-size: 0.78rem;
    color: var(--color-accent, #2563eb);
    font-weight: 600;
  }
  .rel-chip:hover .rel-target {
    color: var(--color-primary, #0f172a);
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .section-heading {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .heading-icon {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .rel-chip {
    background: rgba(96, 165, 250, 0.1);
    border-color: rgba(96, 165, 250, 0.25);
  }
  :global([data-theme="dark"]) .rel-chip:hover {
    background: rgba(96, 165, 250, 0.2);
    border-color: #60a5fa;
  }
  :global([data-theme="dark"]) .rel-icon {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .rel-badge {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .rel-target {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .rel-chip:hover .rel-target {
    color: #ffffff;
  }
</style>
