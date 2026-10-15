<script lang="ts">
  import Icon from '../Icon.svelte';

  export let metrics: Record<string, any> = {};
  export let title: string = 'Telemetry & Scoring Metrics';

  $: entries = Object.entries(metrics || {});
</script>

{#if entries.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name="layers" size={14} /></span>
      <span>{title}</span>
    </h3>
    <div class="metrics-grid">
      {#each entries as [key, val]}
        <div class="metric-card">
          <span class="metric-key">{key.replace(/_/g, ' ').toUpperCase()}</span>
          <span class="metric-val">{val}</span>
        </div>
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
    gap: 0.45rem;
  }
  .heading-icon {
    display: inline-flex;
    align-items: center;
    color: #38bdf8;
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.5rem;
  }
  .metric-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    padding: 0.45rem 0.6rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .metric-key {
    font-size: 0.68rem;
    color: #94a3b8;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .metric-val {
    font-family: var(--font-mono, monospace);
    font-size: 0.85rem;
    color: #38bdf8;
    font-weight: 700;
    word-break: break-all;
  }

  :global([data-theme="light"]) .section-heading,
  :global(body.theme-forensic-dossier) .section-heading {
    color: #475569;
  }
  :global([data-theme="light"]) .heading-icon,
  :global(body.theme-forensic-dossier) .heading-icon {
    color: #0284c7;
  }
  :global([data-theme="light"]) .metric-card,
  :global(body.theme-forensic-dossier) .metric-card {
    background: #f8fafc;
    border-color: #e2e8f0;
  }
  :global([data-theme="light"]) .metric-key,
  :global(body.theme-forensic-dossier) .metric-key {
    color: #64748b;
  }
  :global([data-theme="light"]) .metric-val,
  :global(body.theme-forensic-dossier) .metric-val {
    color: #0369a1;
  }
</style>
