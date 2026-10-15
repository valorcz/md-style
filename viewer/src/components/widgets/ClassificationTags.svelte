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
  .ttp-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .ttp-tag {
    background: rgba(14, 165, 233, 0.12);
    border: 1px solid rgba(14, 165, 233, 0.3);
    color: #7dd3fc;
    font-size: 0.76rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    display: inline-flex;
    gap: 0.25rem;
  }
  .tag-label {
    color: #94a3b8;
    text-transform: capitalize;
  }

  :global([data-theme="light"]) .section-heading,
  :global(body.theme-forensic-dossier) .section-heading {
    color: #475569;
  }
  :global([data-theme="light"]) .heading-icon,
  :global(body.theme-forensic-dossier) .heading-icon {
    color: #0284c7;
  }
  :global([data-theme="light"]) .ttp-tag,
  :global(body.theme-forensic-dossier) .ttp-tag {
    background: #f0f9ff;
    border-color: #bae6fd;
    color: #0369a1;
  }
  :global([data-theme="light"]) .tag-label,
  :global(body.theme-forensic-dossier) .tag-label {
    color: #64748b;
  }
</style>
