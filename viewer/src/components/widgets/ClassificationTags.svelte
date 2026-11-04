<script lang="ts">
  import Icon from '../Icon.svelte';

  export let classification: Record<string, any> = {};
  export let title: string = 'Classification & TTPs';

  $: entries = Object.entries(classification || {});
</script>

{#if entries.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name="target" size={14} /></span>
      <span>{title}</span>
    </h3>
    <div class="ttp-tags">
      {#each entries as [k, val]}
        {#if Array.isArray(val)}
          {#each val as item}
            <span class="ttp-tag"><span class="tag-label">{k}:</span> {item}</span>
          {/each}
        {:else}
          <span class="ttp-tag"><span class="tag-label">{k}:</span> {val}</span>
        {/if}
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
  .ttp-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .ttp-tag {
    background: var(--color-bg-alt, #f1f5f9);
    border: 1px solid var(--color-border, #e2e8f0);
    color: var(--color-text, #0f172a);
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    display: inline-flex;
    gap: 0.25rem;
  }
  .tag-label {
    color: var(--color-text-muted, #64748b);
    text-transform: capitalize;
  }

  :global([data-theme="dark"]) .section-heading {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .heading-icon {
    color: #38bdf8;
  }
  :global([data-theme="dark"]) .ttp-tag {
    background: rgba(14, 165, 233, 0.12);
    border-color: rgba(14, 165, 233, 0.3);
    color: #7dd3fc;
  }
  :global([data-theme="dark"]) .tag-label {
    color: #94a3b8;
  }
</style>
