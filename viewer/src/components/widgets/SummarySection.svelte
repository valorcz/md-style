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
    gap: 0.5rem;
    margin-top: 0.4rem;
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
    display: inline-flex;
    align-items: center;
    color: var(--color-accent, #2563eb);
  }
  .summary-text {
    margin: 0;
    font-size: 0.88rem;
    line-height: 1.6;
    color: var(--color-text, #1e293b);
  }

  :global([data-theme="dark"]) .section-heading {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .heading-icon {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .summary-text {
    color: #e2e8f0;
  }
</style>
