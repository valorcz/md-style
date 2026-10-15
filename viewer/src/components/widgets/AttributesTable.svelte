<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../Icon.svelte';

  export let data: Record<string, any> = {};
  export let title: string = 'Key Attributes';
  export let icon: string = 'file-text';
  export let isDetailsTable: boolean = false;
  export let allEntities: Record<string, any> = {};
  export let checkResolvable: ((target: string) => boolean) | null = null;

  const dispatch = createEventDispatcher<{
    pivot: string;
  }>();

  function isTargetResolvable(target: string): boolean {
    if (!target || typeof target !== 'string') return false;
    const trimmed = target.trim();
    if (allEntities && allEntities[trimmed]) return true;
    if (trimmed.startsWith('CVE-') || trimmed.startsWith('CWE-') || trimmed.startsWith('T1') || trimmed.startsWith('event-')) return true;
    return false;
  }

  $: resolveFn = checkResolvable || isTargetResolvable;

  $: filteredEntries = Object.entries(data || {}).filter(([k]) =>
    k !== 'Investigation Tips' && k !== 'Attacker Behavior' && k !== 'Forensic Role'
  );
</script>

{#if filteredEntries.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name={icon} size={14} /></span>
      <span>{title}</span>
    </h3>
    <table class="attributes-table" class:details-table={isDetailsTable}>
      <tbody>
        {#each filteredEntries as [key, val]}
          <tr>
            <th scope="row">{key}</th>
            <td>
              {#if typeof val === 'string' && resolveFn(val)}
                <button type="button" class="inline-pivot-btn" on:click={() => dispatch('pivot', val)} title="Inspect {val}">
                  {val} ↗
                </button>
              {:else if key === 'Associated CVE' && typeof val === 'string' && val.startsWith('CVE-')}
                <button type="button" class="inline-pivot-btn" on:click={() => dispatch('pivot', val)} title="Inspect {val}">
                  <Icon name="alert-circle" size={12} />
                  <span>{val} ↗</span>
                </button>
              {:else}
                {typeof val === 'object' ? JSON.stringify(val) : val}
              {/if}
            </td>
          </tr>
        {/each}
      </tbody>
    </table>
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
  .attributes-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.8rem;
  }
  .attributes-table th,
  .attributes-table td {
    padding: 0.4rem 0.6rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    vertical-align: top;
    text-align: left;
  }
  .attributes-table th {
    color: #94a3b8;
    font-weight: 600;
    width: 38%;
  }
  .details-table th {
    width: 42%;
  }
  .attributes-table td {
    color: #cbd5e1;
    overflow-wrap: break-word;
    word-break: break-word;
  }
  .inline-pivot-btn {
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.3);
    color: #38bdf8;
    border-radius: 4px;
    padding: 0.15rem 0.45rem;
    font-family: var(--font-mono, monospace);
    font-size: 0.78rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .inline-pivot-btn:hover {
    background: #0284c7;
    border-color: #38bdf8;
    color: #ffffff;
    transform: translateY(-1px);
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
  :global([data-theme="light"]) .attributes-table th,
  :global(body.light-theme) .attributes-table th,
  :global(body.theme-forensic-dossier) .attributes-table th {
    color: #64748b;
    border-bottom-color: rgba(0, 0, 0, 0.06);
  }
  :global([data-theme="light"]) .attributes-table td,
  :global(body.light-theme) .attributes-table td,
  :global(body.theme-forensic-dossier) .attributes-table td {
    color: #334155;
    border-bottom-color: rgba(0, 0, 0, 0.06);
  }
  :global([data-theme="light"]) .inline-pivot-btn,
  :global(body.light-theme) .inline-pivot-btn,
  :global(body.theme-forensic-dossier) .inline-pivot-btn {
    background: rgba(2, 132, 199, 0.08);
    border: 1px solid rgba(2, 132, 199, 0.25);
    color: #0284c7;
  }
  :global([data-theme="light"]) .inline-pivot-btn:hover,
  :global(body.light-theme) .inline-pivot-btn:hover,
  :global(body.theme-forensic-dossier) .inline-pivot-btn:hover {
    background: #0284c7;
    color: #ffffff;
  }
</style>
