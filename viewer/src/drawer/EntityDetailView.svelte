<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import CveCard from '../inspector/families/CveCard.svelte';
  import WinEventCard from '../inspector/families/WinEventCard.svelte';
  import EvtxCard from '../inspector/families/EvtxCard.svelte';
  import CweCard from '../inspector/families/CweCard.svelte';
  import IpCard from '../inspector/families/IpCard.svelte';
  import HashCard from '../inspector/families/HashCard.svelte';
  import MitreCard from '../inspector/families/MitreCard.svelte';
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

  function getTypeIcon(type: string): string {
    const t = (type || '').toLowerCase();
    if (t === 'cve') return '🛡️';
    if (t === 'cwe') return '🧩';
    if (t === 'ghsa') return '📢';
    if (t === 'mitre') return '⚔️';
    if (t === 'winevent') return '📋';
    if (t === 'evtx') return '🗄️';
    if (t === 'ip') return '🌐';
    if (t === 'hash') return '#️⃣';
    if (t === 'registry') return '🗝️';
    if (t === 'network') return '🌐';
    if (t === 'statute' || t === 'law') return '⚖️';
    if (t === 'ico' || t === 'company' || t === 'ares') return '🏢';
    if (t === 'iban' || t === 'bank') return '💳';
    return '📦';
  }
</script>

<div class="entity-detail-container">
  <!-- Hero Card -->
  <div class="entity-hero-card type-{(entity.type || 'entity').toLowerCase()}">
    <div class="hero-top-row">
      <span class="hero-type-tag">
        <span class="hero-type-icon">{getTypeIcon(entity.type)}</span>
        {(entity.type || 'entity').toUpperCase()}
      </span>
      <div class="hero-badges">
        {#if entity.provenance?.source?.startsWith('transitive:')}
          <span class="badge badge-transitive" title="Inferred via graph closure from {entity.provenance.source.replace('transitive:', '')}">
            🔗 CONNECTED INTEL
          </span>
        {/if}
        <span class="badge badge-{entity.severity?.toLowerCase() || 'info'}">
          {entity.severity || 'INFO'}
        </span>
        {#if entity.badge}
          <span class="badge badge-meta">{entity.badge}</span>
        {/if}
      </div>
    </div>

    <h2 class="entity-title">{entity.title || entity.label || entity.id}</h2>

    <div class="token-row">
      <code class="entity-id" title="Artifact Value">{entity.id}</code>
      <button
        class="copy-btn"
        class:is-copied={copiedField === 'id'}
        on:click={() => copyToClipboard(entity.id, 'id')}
        title="Copy Artifact Value"
      >
        <Icon name={copiedField === 'id' ? 'check' : 'copy'} size={13} />
        <span>{copiedField === 'id' ? 'Copied!' : 'Copy Artifact'}</span>
      </button>
      <button
        class="copy-btn copy-btn-subtle"
        class:is-copied={copiedField === 'json'}
        on:click={() => copyToClipboard(JSON.stringify(entity, null, 2), 'json')}
        title="Copy Complete Entity JSON"
      >
        <Icon name={copiedField === 'json' ? 'check' : 'code'} size={13} />
        <span>{copiedField === 'json' ? 'Copied JSON!' : 'JSON'}</span>
      </button>
    </div>
  </div>

  <!-- Bespoke Family Cards & Extensible Schema Router -->
  <div class="family-card-wrapper">
    {#if (entity.type || '').toLowerCase() === 'cve'}
      <CveCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'winevent'}
      <WinEventCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'evtx'}
      <EvtxCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'cwe'}
      <CweCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'ip'}
      <IpCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'hash'}
      <HashCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else if (entity.type || '').toLowerCase() === 'mitre'}
      <MitreCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {:else}
      <DynamicSchemaCard {entity} {allEntities} {checkResolvable} {i18n} on:pivot={(e) => dispatch('pivot', e.detail)} />
    {/if}
  </div>

  <!-- Provenance Footer -->
  {#if entity.provenance}
    <footer class="drawer-footer">
      <small class="provenance-stamp">
        {i18n.provenance || 'Provenance'}: <strong>{entity.provenance.source}</strong> ·
        {i18n.status || 'Status'}: {entity.provenance.status}
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
    gap: 1.25rem;
    flex: 1;
  }
  .entity-hero-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 8px;
    padding: 1rem 1.15rem;
    display: flex;
    flex-direction: column;
    gap: 0.65rem;
    position: relative;
    overflow: hidden;
  }
  .entity-hero-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    bottom: 0;
    width: 4px;
    background: #38bdf8;
  }
  .entity-hero-card.type-cve::before { background: #ef4444; }
  .entity-hero-card.type-cwe::before { background: #f59e0b; }
  .entity-hero-card.type-winevent::before { background: #00f0ff; }
  .entity-hero-card.type-mitre::before { background: #f97316; }
  .entity-hero-card.type-evtx::before { background: #a855f7; }
  .entity-hero-card.type-statute::before,
  .entity-hero-card.type-law::before { background: #10b981; }

  .hero-top-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }
  .hero-type-tag {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
    letter-spacing: 0.05em;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .hero-type-icon {
    font-size: 0.95rem;
  }
  .hero-badges {
    display: flex;
    gap: 0.4rem;
    align-items: center;
  }
  .badge {
    font-size: 0.72rem;
    font-weight: 700;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }
  .badge-critical { background: #ef4444; color: #fff; }
  .badge-high { background: #f97316; color: #fff; }
  .badge-medium { background: #eab308; color: #000; }
  .badge-info { background: #3b82f6; color: #fff; }
  .badge-meta {
    background: rgba(255, 255, 255, 0.1);
    color: #94a3b8;
  }
  .badge-transitive {
    background: rgba(168, 85, 247, 0.2);
    color: #c084fc;
    border: 1px solid rgba(168, 85, 247, 0.4);
  }

  .entity-title {
    font-size: 1.15rem;
    font-weight: 700;
    margin: 0;
    line-height: 1.35;
    color: #f8fafc;
  }
  .token-row {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-wrap: wrap;
  }
  .entity-id {
    font-family: var(--font-mono, monospace);
    font-size: 0.82rem;
    background: rgba(255, 255, 255, 0.06);
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    color: #38bdf8;
  }
  .copy-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    font-size: 0.75rem;
    font-weight: 600;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.35);
    color: #38bdf8;
    border-radius: 4px;
    padding: 0.25rem 0.6rem;
    cursor: pointer;
    transition: all 0.15s ease;
    white-space: nowrap;
    font-family: inherit;
  }
  .copy-btn:hover {
    background: rgba(56, 189, 248, 0.22);
    border-color: #38bdf8;
    color: #f0f9ff;
  }
  .copy-btn.is-copied {
    background: #10b981 !important;
    border-color: #10b981 !important;
    color: #ffffff !important;
  }
  .copy-btn-subtle {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.18);
    color: #94a3b8;
  }
  .copy-btn-subtle:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #e2e8f0;
    border-color: #cbd5e1;
  }
  .family-card-wrapper {
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
  }
  .drawer-footer {
    margin-top: auto;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
  .provenance-stamp {
    font-size: 0.72rem;
    color: #64748b;
  }

  /* Light Theme */
  :global([data-theme="light"]) .entity-hero-card,
  :global(body.light-theme) .entity-hero-card {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  }
  :global([data-theme="light"]) .entity-title,
  :global(body.light-theme) .entity-title {
    color: #0f172a;
  }
  :global([data-theme="light"]) .entity-id,
  :global(body.light-theme) .entity-id {
    background: rgba(0, 0, 0, 0.05);
    color: #0284c7;
  }
  :global([data-theme="light"]) .badge-transitive,
  :global(body.light-theme) .badge-transitive {
    background: rgba(147, 51, 234, 0.1);
    color: #7e22ce;
    border: 1px solid rgba(147, 51, 234, 0.3);
  }
</style>
