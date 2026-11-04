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
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.05em;
    color: var(--color-text-muted, #64748b);
    text-transform: uppercase;
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .heading-icon {
    display: inline-flex;
    align-items: center;
    color: var(--color-text-muted, #64748b);
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.5rem;
  }
  .metric-card {
    background: var(--color-bg-alt, #f8fafc);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    padding: 0.5rem 0.65rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .metric-key {
    font-size: 0.68rem;
    color: var(--color-text-muted, #64748b);
    font-weight: 600;
    letter-spacing: 0.05em;
  }
  .metric-val {
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 0.9rem;
    color: var(--color-text, #0f172a);
    font-weight: 600;
    word-break: break-all;
  }

  :global([data-theme="dark"]) .section-heading {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .heading-icon {
    color: #38bdf8;
  }
  :global([data-theme="dark"]) .metric-card {
    background: rgba(255, 255, 255, 0.04);
    border-color: rgba(255, 255, 255, 0.08);
  }
  :global([data-theme="dark"]) .metric-key {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .metric-val {
    color: #38bdf8;
    font-family: var(--font-mono, monospace);
  }
</style>
