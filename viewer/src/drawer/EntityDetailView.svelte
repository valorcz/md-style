<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import DynamicSchemaCard from '../inspector/families/DynamicSchemaCard.svelte';

  export let entity: any;
  export let allEntities: Record<string, any> = {};
  export let checkResolvable: ((t: string) => boolean) | null = null;
  export let i18n: Record<string, string> = {};

  const dispatch = createEventDispatcher<{
    pivot: string;
  }>();

  let copiedField: string | null = null;
  let copiedTimeout: any = null;

  function copyToClipboard(text: string, fieldName: string = 'id') {
    if (!text) return;
    const doCopy = () => {
      copiedField = fieldName;
      if (copiedTimeout) clearTimeout(copiedTimeout);
      copiedTimeout = setTimeout(() => {
        copiedField = null;
      }, 1800);
    };

    if (navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(text).then(doCopy).catch(() => {
        fallbackCopy(text);
        doCopy();
      });
    } else {
      fallbackCopy(text);
      doCopy();
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

  function getTypeLabel(type: string): string {
    const t = (type || '').toLowerCase();
    if (t === 'statute' || t === 'law') return 'Právní předpis / Zákon';
    if (t === 'standard') return 'Technický standard';
    if (t === 'authority' || t === 'institution') return 'Státní orgán / Dozor';
    if (t === 'ico' || t === 'company' || t === 'ares') return 'Organizace / Subjekt';
    if (t === 'cve' || t === 'cwe' || t === 'vulnerability') return 'Bezpečnostní zranitelnost';
    if (t === 'mitre') return 'Taktika / Technika';
    return (type || 'Pojem').toUpperCase();
  }
</script>

<div class="entity-detail-container">
  <!-- Hero Card -->
  <div class="entity-hero-card">
    <div class="hero-top-row">
      <span class="hero-type-tag">
        {getTypeLabel(entity.type)}
      </span>
      {#if entity.severity && entity.severity !== 'INFO'}
        <span class="badge badge-{entity.severity.toLowerCase()}">
          {entity.severity}
        </span>
      {/if}
    </div>

    <h2 class="entity-title">{entity.title || entity.label || entity.id}</h2>

    <div class="token-row">
      <code class="entity-id" title="Identifikátor">{entity.id}</code>
      <button
        class="copy-btn"
        class:is-copied={copiedField === 'id'}
        on:click={() => copyToClipboard(entity.id, 'id')}
        title="Kopírovat identifikátor"
      >
        <Icon name={copiedField === 'id' ? 'check' : 'copy'} size={12} />
        <span>{copiedField === 'id' ? 'Zkopírováno' : 'Kopírovat'}</span>
      </button>
      {#if entity.attributes || entity.metrics}
        <button
          class="copy-btn copy-btn-subtle"
          class:is-copied={copiedField === 'json'}
          on:click={() => copyToClipboard(JSON.stringify(entity, null, 2), 'json')}
          title="Kopírovat data JSON"
        >
          <Icon name={copiedField === 'json' ? 'check' : 'code'} size={12} />
          <span>{copiedField === 'json' ? 'JSON zkopírován' : 'JSON'}</span>
        </button>
      {/if}
    </div>
  </div>

  <!-- Bespoke Family Cards & Extensible Schema Router -->
  <div class="family-card-wrapper">
    <DynamicSchemaCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
  </div>

  <!-- Provenance Footer -->
  {#if entity.provenance}
    <footer class="drawer-footer">
      <small class="provenance-stamp">
        {i18n.provenance || 'Zdroj'}: <strong>{entity.provenance.source}</strong>
        {#if entity.provenance.fetched_at}
          · {new Date(entity.provenance.fetched_at).toLocaleDateString()}
        {/if}
      </small>
    </footer>
  {/if}
</div>

<style>
  .entity-detail-container {
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
    flex: 1;
  }
  .entity-hero-card {
    background: var(--color-paper, #ffffff);
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    padding: 1rem 1.15rem;
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }

  .hero-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .hero-type-tag {
    font-size: 0.68rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: var(--color-accent, #2563eb);
  }
  .badge {
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .badge-critical { background: rgba(239, 68, 68, 0.12); color: #dc2626; border: 1px solid rgba(239, 68, 68, 0.3); }
  .badge-high { background: rgba(249, 115, 22, 0.12); color: #ea580c; border: 1px solid rgba(249, 115, 22, 0.3); }
  .badge-medium { background: rgba(234, 179, 8, 0.14); color: #b45309; border: 1px solid rgba(234, 179, 8, 0.3); }
  .badge-info { background: rgba(37, 99, 235, 0.08); color: #2563eb; }

  .entity-title {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.35;
    color: var(--color-primary, #0f172a);
  }
  .token-row {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    flex-wrap: wrap;
    margin-top: 0.15rem;
  }
  .entity-id {
    font-family: var(--font-mono, monospace);
    font-size: 0.78rem;
    background: rgba(0, 0, 0, 0.04);
    padding: 0.2rem 0.45rem;
    border-radius: 4px;
    color: var(--color-accent, #2563eb);
  }
  .copy-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-size: 0.74rem;
    font-weight: 600;
    background: rgba(37, 99, 235, 0.08);
    border: none;
    color: var(--color-accent, #2563eb);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
    white-space: nowrap;
    font-family: inherit;
  }
  .copy-btn:hover {
    background: rgba(37, 99, 235, 0.16);
    color: var(--color-primary, #0f172a);
  }
  .copy-btn.is-copied {
    background: #059669 !important;
    color: #ffffff !important;
  }
  .copy-btn-subtle {
    background: transparent;
    color: var(--color-text-muted, #64748b);
  }
  .copy-btn-subtle:hover {
    background: rgba(0, 0, 0, 0.04);
    color: var(--color-text, #0f172a);
  }

  .family-card-wrapper {
    display: flex;
    flex-direction: column;
    gap: 1.1rem;
  }
  .drawer-footer {
    margin-top: auto;
    padding-top: 0.85rem;
    border-top: 1px solid var(--color-border, rgba(0, 0, 0, 0.06));
  }
  .provenance-stamp {
    font-size: 0.72rem;
    color: var(--color-text-muted, #64748b);
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .entity-hero-card {
    background: #23252a;
    border-color: #2e323b;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  }
  :global([data-theme="dark"]) .hero-type-tag {
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .entity-title {
    color: #f1f5f9;
  }
  :global([data-theme="dark"]) .entity-id {
    background: rgba(255, 255, 255, 0.06);
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .copy-btn {
    background: rgba(96, 165, 250, 0.12);
    color: #60a5fa;
  }
  :global([data-theme="dark"]) .copy-btn:hover {
    background: rgba(96, 165, 250, 0.2);
    color: #ffffff;
  }
  :global([data-theme="dark"]) .copy-btn-subtle {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .copy-btn-subtle:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #f1f5f9;
  }
  :global([data-theme="dark"]) .drawer-footer {
    border-top-color: #262930;
  }
  :global([data-theme="dark"]) .provenance-stamp {
    color: #94a3b8;
  }
</style>
