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

  let copiedKey: string | null = null;
  let copiedTimeout: any = null;

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

  function isWideValue(val: any, key: string): boolean {
    if (val === null || val === undefined) return false;
    if (typeof val === 'object') return true;
    const str = String(val);
    return str.length > 26 || str.includes('\n') || key.length > 22;
  }

  function copyValue(text: string, key: string) {
    if (!text) return;
    copiedKey = key;
    if (copiedTimeout) clearTimeout(copiedTimeout);
    copiedTimeout = setTimeout(() => {
      copiedKey = null;
    }, 1600);

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).catch(() => fallbackCopy(text));
    } else {
      fallbackCopy(text);
    }
  }

  function fallbackCopy(text: string) {
    const el = document.createElement('textarea');
    el.value = text;
    el.style.position = 'fixed';
    el.style.opacity = '0';
    document.body.appendChild(el);
    el.select();
    try { document.execCommand('copy'); } catch (_) {}
    document.body.removeChild(el);
  }
</script>

{#if filteredEntries.length > 0}
  <div class="drawer-section">
    <h3 class="section-heading">
      <span class="heading-icon"><Icon name={icon} size={14} /></span>
      <span>{title}</span>
    </h3>

    <div class="property-grid" class:details-grid={isDetailsTable}>
      {#each filteredEntries as [key, val]}
        {@const wide = isWideValue(val, key)}
        <div class="property-tile" class:is-wide={wide}>
          <div class="tile-header">
            <span class="property-key" title={key}>{key}</span>
            {#if typeof val === 'string' || typeof val === 'number'}
              <button
                type="button"
                class="mini-copy-btn"
                class:is-copied={copiedKey === key}
                on:click={() => copyValue(String(val), key)}
                title="Kopírovat hodnotu"
                aria-label="Kopírovat {key}"
              >
                <Icon name={copiedKey === key ? 'check' : 'copy'} size={11} />
              </button>
            {/if}
          </div>

          <div class="property-value">
            {#if typeof val === 'string' && resolveFn(val)}
              <button type="button" class="inline-pivot-btn" on:click={() => dispatch('pivot', val)} title="Zobrazit detail {val}">
                <span>{val}</span>
                <span class="pivot-arrow">↗</span>
              </button>
            {:else if key === 'Associated CVE' && typeof val === 'string' && val.startsWith('CVE-')}
              <button type="button" class="inline-pivot-btn" on:click={() => dispatch('pivot', val)} title="Zobrazit detail {val}">
                <Icon name="alert-circle" size={11} />
                <span>{val}</span>
                <span class="pivot-arrow">↗</span>
              </button>
            {:else if typeof val === 'boolean'}
              <span class="bool-badge" class:is-true={val}>{val ? 'Ano' : 'Ne'}</span>
            {:else if Array.isArray(val)}
              <div class="array-tags">
                {#each val as item}
                  <span class="array-tag">{item}</span>
                {/each}
              </div>
            {:else if typeof val === 'object' && val !== null}
              <pre class="object-preview">{JSON.stringify(val, null, 2)}</pre>
            {:else}
              <span class="text-value">{val}</span>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  </div>
{/if}

<style>
  .drawer-section {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
    margin-top: 0.35rem;
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

  .property-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 0.45rem;
    width: 100%;
    box-sizing: border-box;
  }

  .property-tile {
    background: rgba(0, 0, 0, 0.02);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 6px;
    padding: 0.45rem 0.6rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    min-width: 0;
    transition: border-color 0.15s ease, background 0.15s ease;
    box-sizing: border-box;
  }

  .property-tile:hover {
    background: rgba(0, 0, 0, 0.035);
    border-color: rgba(37, 99, 235, 0.3);
  }

  .property-tile.is-wide {
    grid-column: span 2;
  }

  .tile-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.3rem;
  }

  .property-key {
    font-size: 0.64rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    color: var(--color-text-muted, #64748b);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .mini-copy-btn {
    opacity: 0;
    background: transparent;
    border: none;
    padding: 0.1rem;
    margin: 0;
    color: var(--color-text-muted, #64748b);
    cursor: pointer;
    border-radius: 3px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: opacity 0.15s ease, color 0.15s ease;
  }

  .property-tile:hover .mini-copy-btn {
    opacity: 0.8;
  }

  .mini-copy-btn:hover {
    opacity: 1 !important;
    color: var(--color-primary, #0f172a);
  }

  .mini-copy-btn.is-copied {
    opacity: 1 !important;
    color: #059669 !important;
  }

  .property-value {
    font-size: 0.82rem;
    font-weight: 500;
    color: var(--color-text, #0f172a);
    line-height: 1.35;
    word-break: break-word;
  }

  .text-value {
    display: inline-block;
  }

  .inline-pivot-btn {
    background: rgba(37, 99, 235, 0.08);
    border: none;
    color: var(--color-accent, #2563eb);
    border-radius: 4px;
    padding: 0.15rem 0.4rem;
    font-family: inherit;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    max-width: 100%;
  }

  .inline-pivot-btn:hover {
    background: rgba(37, 99, 235, 0.16);
    color: var(--color-primary, #0f172a);
  }

  .pivot-arrow {
    font-size: 0.72rem;
    line-height: 1;
  }

  .bool-badge {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.1rem 0.4rem;
    border-radius: 3px;
    display: inline-block;
    background: rgba(220, 38, 38, 0.1);
    color: #dc2626;
  }

  .bool-badge.is-true {
    background: rgba(5, 150, 105, 0.12);
    color: #059669;
  }

  .array-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
  }

  .array-tag {
    font-size: 0.7rem;
    background: rgba(0, 0, 0, 0.05);
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    color: var(--color-text, #334155);
  }

  .object-preview {
    margin: 0;
    font-family: var(--font-mono, monospace);
    font-size: 0.7rem;
    background: rgba(0, 0, 0, 0.04);
    padding: 0.35rem;
    border-radius: 4px;
    overflow-x: auto;
  }

  /* Dark Theme */
  :global([data-theme="dark"] .section-heading) {
    color: #94a3b8;
  }
  :global([data-theme="dark"] .heading-icon) {
    color: #60a5fa;
  }
  :global([data-theme="dark"] .property-tile) {
    background: rgba(255, 255, 255, 0.03);
    border-color: #2e323b;
  }
  :global([data-theme="dark"] .property-tile:hover) {
    background: rgba(255, 255, 255, 0.05);
    border-color: rgba(96, 165, 250, 0.35);
  }
  :global([data-theme="dark"] .property-key) {
    color: #94a3b8;
  }
  :global([data-theme="dark"] .property-value) {
    color: #f1f5f9;
  }
  :global([data-theme="dark"] .mini-copy-btn:hover) {
    color: #ffffff;
  }
  :global([data-theme="dark"] .inline-pivot-btn) {
    background: rgba(96, 165, 250, 0.12);
    color: #60a5fa;
  }
  :global([data-theme="dark"] .inline-pivot-btn:hover) {
    background: rgba(96, 165, 250, 0.22);
    color: #ffffff;
  }
  :global([data-theme="dark"] .array-tag) {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
  }
  :global([data-theme="dark"] .object-preview) {
    background: rgba(255, 255, 255, 0.06);
    color: #e2e8f0;
  }
</style>
