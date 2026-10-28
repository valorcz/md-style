<script lang="ts">
  import Icon from '../Icon.svelte';

  export let references: Array<{ url: string; title?: string }> = [];
  export let title: string = 'Verified References';
</script>

{#if references && references.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name="external-link" size={14} /></span>
      <span>{title}</span>
    </h3>
    <ul class="references-list">
      {#each references as ref}
        <li>
          <a href={ref.url} target="_blank" rel="noopener noreferrer">
            {ref.title || ref.url} ↗
          </a>
        </li>
      {/each}
    </ul>
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
  .references-list {
    list-style: none;
    padding: 0;
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }
  .references-list li {
    font-size: 0.85rem;
    line-height: 1.4;
  }
  .references-list a {
    color: #38bdf8;
    text-decoration: none;
    word-break: break-all;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }
  .references-list a:hover {
    text-decoration: underline;
  }

  :global([data-theme="light"]) .section-heading,
  :global(body.theme-forensic-dossier) .section-heading {
    color: #475569;
  }
  :global([data-theme="light"]) .heading-icon,
  :global(body.theme-forensic-dossier) .heading-icon {
    color: #0284c7;
  }
  :global([data-theme="light"]) .references-list a,
  :global(body.theme-forensic-dossier) .references-list a {
    color: #0284c7;
  }
</style>
