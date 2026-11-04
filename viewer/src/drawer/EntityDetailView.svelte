<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import Badge from '../components/ui/Badge.svelte';
  import Button from '../components/ui/Button.svelte';
  import IconButton from '../components/ui/IconButton.svelte';
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

  function scrollToEntityOccurrence() {
    if (!entity?.id) return;
    try {
      const escapedId = typeof CSS !== 'undefined' && CSS.escape ? CSS.escape(entity.id) : entity.id;
      const selector = `.inspectable[data-token="${escapedId}"], .inspectable[data-value="${escapedId}"]`;
      let target = document.querySelector(selector) as HTMLElement | null;
      if (!target) {
        const allInspectables = document.querySelectorAll('.inspectable');
        for (const el of allInspectables) {
          if (el.textContent?.trim() === entity.id || el.textContent?.trim() === entity.title) {
            target = el as HTMLElement;
            break;
          }
        }
      }
      if (target) {
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
        target.classList.add('entity-highlight-pulse');
        setTimeout(() => {
          target?.classList.remove('entity-highlight-pulse');
        }, 2200);
      }
    } catch (_) {}
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

  function getSeverityColor(sev: string): string {
    const s = (sev || '').toUpperCase();
    if (s === 'CRITICAL') return '#dc2626';
    if (s === 'HIGH') return '#ea580c';
    if (s === 'MEDIUM') return '#b45309';
    return 'var(--color-accent, #2563eb)';
  }
</script>

<div class="entity-detail-container">
  <!-- Hero Card -->
  <div class="entity-hero-card">
    <div class="hero-top-row">
      <Badge variant="subtle" color="var(--color-accent, #2563eb)" size="sm">
        {getTypeLabel(entity.type)}
      </Badge>
      {#if entity.severity && entity.severity !== 'INFO'}
        <Badge variant="solid" color={getSeverityColor(entity.severity)} size="sm">
          {entity.severity}
        </Badge>
      {/if}
    </div>

    <h2 class="entity-title">{entity.title || entity.label || entity.id}</h2>

    <div class="token-row">
      <code class="entity-id" title="Identifikátor">{entity.id}</code>
      <Button
        variant={copiedField === 'id' ? 'primary' : 'secondary'}
        size="sm"
        icon={copiedField === 'id' ? 'check' : 'copy'}
        on:click={() => copyToClipboard(entity.id, 'id')}
        title="Kopírovat identifikátor do schránky"
      >
        <span>{copiedField === 'id' ? 'Zkopírováno' : 'Kopírovat'}</span>
      </Button>

      {#if entity.attributes || entity.metrics}
        <Button
          variant="ghost"
          size="sm"
          icon={copiedField === 'json' ? 'check' : 'code'}
          on:click={() => copyToClipboard(JSON.stringify(entity, null, 2), 'json')}
          title="Kopírovat kompletní data entity ve formátu JSON"
        >
          <span>{copiedField === 'json' ? 'JSON zkopírován' : 'JSON'}</span>
        </Button>
      {/if}

      <Button
        variant="ghost"
        size="sm"
        icon="corner-down-right"
        on:click={scrollToEntityOccurrence}
        title="Přejít na výskyt entity v dokumentu"
      >
        <span>Najít v textu</span>
      </Button>
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
    padding: 1.1rem 1.2rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    box-shadow: 0 1px 3px rgba(15, 23, 42, 0.04);
  }

  .hero-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

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
    gap: 0.5rem;
    flex-wrap: wrap;
    margin-top: 0.2rem;
  }

  .entity-id {
    font-family: var(--font-mono, monospace);
    font-size: 0.78rem;
    background: rgba(0, 0, 0, 0.04);
    padding: 0.2rem 0.45rem;
    border-radius: 4px;
    color: var(--color-accent, #2563eb);
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

  :global(.entity-highlight-pulse) {
    outline: 2px solid var(--color-accent, #2563eb) !important;
    outline-offset: 3px !important;
    background: rgba(37, 99, 235, 0.18) !important;
    border-radius: 3px !important;
    transition: outline 0.3s ease, background 0.3s ease !important;
  }

  /* Dark Theme */
  :global([data-theme="dark"] .entity-hero-card) {
    background: #23252a;
    border-color: #2e323b;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
  }
  :global([data-theme="dark"] .entity-title) {
    color: #f1f5f9;
  }
  :global([data-theme="dark"] .entity-id) {
    background: rgba(255, 255, 255, 0.06);
    color: #60a5fa;
  }
  :global([data-theme="dark"] .drawer-footer) {
    border-top-color: #262930;
  }
  :global([data-theme="dark"] .provenance-stamp) {
    color: #94a3b8;
  }
</style>
