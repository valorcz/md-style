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
    display: flex;
    align-items: center;
    color: var(--color-accent, #2563eb);
  }
  .attributes-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .attributes-table th,
  .attributes-table td {
    padding: 0.45rem 0.6rem;
    border-bottom: 1px solid var(--color-border, #f1f5f9);
    vertical-align: top;
    text-align: left;
  }
  .attributes-table th {
    color: var(--color-text-muted, #64748b);
    font-weight: 600;
    width: 38%;
  }
  .details-table th {
    width: 42%;
  }
  .attributes-table td {
    color: var(--color-text, #1e293b);
    overflow-wrap: break-word;
    word-break: break-word;
  }
  .inline-pivot-btn {
    background: rgba(37, 99, 235, 0.08);
    border: none;
    color: var(--color-accent, #2563eb);
    border-radius: 4px;
    padding: 0.15rem 0.45rem;
    font-family: inherit;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
  }
  .inline-pivot-btn:hover {
    background: rgba(37, 99, 235, 0.16);
    color: var(--color-primary, #0f172a);
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .section-heading {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .heading-icon {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .attributes-table th {
    color: #94a3b8;
    border-bottom-color: #262930;
  }
  :global([data-theme="dark"]) .attributes-table td {
    color: #e2e8f0;
    border-bottom-color: #262930;
  }
  :global([data-theme="dark"]) .inline-pivot-btn {
    background: rgba(96, 165, 250, 0.12);
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .inline-pivot-btn:hover {
    background: rgba(96, 165, 250, 0.2);
    color: #ffffff;
  }
</style>
