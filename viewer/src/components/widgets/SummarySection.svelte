<script lang="ts">
  import Icon from '../Icon.svelte';

  export let summary: string = '';
  export let title: string = 'Summary';
</script>

{#if summary}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name="file-text" size={14} /></span>
      <span>{title}</span>
    </h3>
    <p class="summary-text">{summary}</p>
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
  .summary-text {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.55;
    color: #e2e8f0;
  }

  :global([data-theme="light"]) .section-heading,
  :global(body.theme-forensic-dossier) .section-heading {
    color: #475569;
  }
  :global([data-theme="light"]) .heading-icon,
  :global(body.theme-forensic-dossier) .heading-icon {
    color: #0284c7;
  }
  :global([data-theme="light"]) .summary-text,
  :global(body.theme-forensic-dossier) .summary-text {
    color: #1e293b;
  }
</style>
