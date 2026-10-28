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
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.04em;
    color: #94a3b8;
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .heading-icon {
    display: flex;
    align-items: center;
    color: #38bdf8;
  }
  .relationship-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .rel-chip {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    padding: 0.3rem 0.55rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    cursor: pointer;
    transition: all 0.15s ease;
    text-align: left;
  }
  .rel-chip:hover {
    background: #0284c7;
    border-color: #38bdf8;
    transform: translateY(-1px);
  }
  .rel-icon {
    display: flex;
    align-items: center;
    color: #38bdf8;
  }
  .rel-chip:hover .rel-icon {
    color: #ffffff;
  }
  .rel-badge {
    font-size: 0.68rem;
    color: #94a3b8;
    text-transform: uppercase;
    font-weight: 500;
  }
  .rel-chip:hover .rel-badge {
    color: #e0f2fe;
  }
  .rel-target {
    font-family: var(--font-mono, monospace);
    font-size: 0.78rem;
    color: #38bdf8;
    font-weight: 600;
  }
  .rel-chip:hover .rel-target {
    color: #ffffff;
  }

  /* Light Theme */
  :global([data-theme="light"]) .section-heading,
  :global(body.light-theme) .section-heading,
  :global(body.theme-forensic-dossier) .section-heading {
    color: #64748b;
  }
  :global([data-theme="light"]) .heading-icon,
  :global(body.light-theme) .heading-icon,
  :global(body.theme-forensic-dossier) .heading-icon {
    color: #0284c7;
  }
  :global([data-theme="light"]) .rel-chip,
  :global(body.light-theme) .rel-chip,
  :global(body.theme-forensic-dossier) .rel-chip {
    background: #f1f5f9;
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .rel-chip:hover,
  :global(body.light-theme) .rel-chip:hover,
  :global(body.theme-forensic-dossier) .rel-chip {
    background: #0284c7;
    border-color: #0284c7;
  }
  :global([data-theme="light"]) .rel-chip:hover .rel-target,
  :global(body.light-theme) .rel-chip:hover .rel-target,
  :global(body.theme-forensic-dossier) .rel-chip:hover .rel-target {
    color: #ffffff;
  }
</style>
