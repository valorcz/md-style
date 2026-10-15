<script lang="ts">
  export let entity: any = null;
  export let isOpen: boolean = false;
  export let i18n: Record<string, string> = {};
  export let allEntities: Record<string, any> = {};
  export let hasSourceMarkdown: boolean = false;
  export let onClose: () => void = () => {};
  export let onSelectEntity: (e: any) => void = () => {};
  export let onDownloadSource: () => void = () => {};

  import { tick } from 'svelte';
  import { annotationStore } from './annotations/store';
  import AnnotationCard from './annotations/AnnotationCard.svelte';
  import { exportUpdatedHtmlBundle, exportCriticMarkdown } from './annotations/export-bundle';
  import Icon from './components/Icon.svelte';

  export let activeTab: 'kb' | 'comments' = 'kb';
  let searchQuery: string = '';
  let selectedCategory: string = 'all';

  $: if (activeTab === 'comments' && $annotationStore.activeAnnotationId && drawerContainer) {
    tick().then(() => {
      const activeEl = drawerContainer?.querySelector('.annotation-card.is-active');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && isOpen) {
      onClose();
    }
  }

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
    return '📦';
  }

  function getCvssClass(score: any): string {
    const num = parseFloat(score);
    if (isNaN(num)) return 'info';
    if (num >= 9.0) return 'critical';
    if (num >= 7.0) return 'high';
    if (num >= 4.0) return 'medium';
    return 'low';
  }

  function splitPipeList(val: string): string[] {
    if (!val || typeof val !== 'string') return [];
    return val.split('|').map(s => s.trim()).filter(Boolean);
  }

  function isTargetResolvable(targetId: string): boolean {
    if (!targetId || typeof targetId !== 'string') return false;
    const clean = targetId.trim().toLowerCase();
    return entityList.some(e =>
      (e.id || '').toLowerCase() === clean ||
      (e.aliases || []).some((a: string) => a.toLowerCase() === clean)
    );
  }

  function selectRelatedTarget(targetId: string) {
    if (!targetId) return;
    const clean = targetId.trim().toLowerCase();
    const found = entityList.find(e =>
      (e.id || '').toLowerCase() === clean ||
      (e.aliases || []).some((a: string) => a.toLowerCase() === clean) ||
      (e.id && e.id.toLowerCase().endsWith('.evtx') && clean.endsWith('.evtx') && (e.id.toLowerCase().includes(clean) || clean.includes(e.id.toLowerCase())))
    );
    if (found) {
      entity = found;
      onSelectEntity(found);
      if (drawerContainer) drawerContainer.scrollTop = 0;
    }
  }

  let drawerContainer: HTMLElement | null = null;

  $: if (entity && drawerContainer) {
    drawerContainer.scrollTop = 0;
  }

  $: entityList = Object.values(allEntities || {});

  $: categories = (() => {
    const counts: Record<string, number> = {};
    for (const e of entityList) {
      const type = (e.type || 'entity').toLowerCase();
      counts[type] = (counts[type] || 0) + 1;
    }
    return counts;
  })();

  $: filteredEntities = entityList.filter(e => {
    const q = searchQuery.toLowerCase().trim();
    const type = (e.type || 'entity').toLowerCase();
    const matchesCat = selectedCategory === 'all' || type === selectedCategory;
    if (!matchesCat) return false;
    if (!q) return true;
    return (
      (e.id || '').toLowerCase().includes(q) ||
      (e.title || '').toLowerCase().includes(q) ||
      (e.summary || '').toLowerCase().includes(q)
    );
  });
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <aside bind:this={drawerContainer} class="drawer-container" aria-label="Entity Details Inspector">
    <!-- Header -->
    <header class="drawer-header">
      {#if activeTab === 'kb' && entity}
        <button class="nav-back-btn" on:click={() => { entity = null; }}>
          <Icon name="chevron-left" size={13} />
          <span>{i18n.all_entities || 'All Entities'}</span>
        </button>
        <div class="header-badges">
          <span class="badge badge-{entity.severity?.toLowerCase() || 'info'}">
            {entity.severity || 'INFO'}
          </span>
          {#if entity.badge}
            <span class="badge badge-meta">{entity.badge}</span>
          {/if}
        </div>
      {:else}
        <div class="header-tab-bar">
          <button
            class="header-tab-btn"
            class:active={activeTab === 'kb'}
            on:click={() => { activeTab = 'kb'; }}
          >
            <Icon name="layers" size={13} />
            <span>{i18n.knowledge_inspector || 'Entities'} ({entityList.length})</span>
          </button>
          <button
            class="header-tab-btn"
            class:active={activeTab === 'comments'}
            on:click={() => { activeTab = 'comments'; entity = null; }}
          >
            <Icon name="message-square" size={13} />
            <span>Review ({$annotationStore.annotations.length})</span>
          </button>
        </div>
      {/if}
      <button class="close-btn" on:click={onClose} aria-label={i18n.close || 'Close'}>
        <Icon name="x" size={15} />
      </button>
    </header>

    <div class="drawer-body">
      {#if activeTab === 'kb' && entity}
        <!-- Single Entity Detail View (Family-Specific Rich Formatting) -->
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

        <!-- CVE Specific Scoring & Threat Banner -->
        {#if (entity.type || '').toLowerCase() === 'cve'}
          {#if entity.metrics?.cvss || entity.metrics?.cvss_v3 || entity.metrics?.cvss_v4 || entity.details?.['CVSS Score']}
            {@const score = entity.metrics?.cvss || entity.metrics?.cvss_v3 || entity.metrics?.cvss_v4 || entity.details?.['CVSS Score']}
            <div class="cvss-hero-gauge cvss-{getCvssClass(score)}">
              <div class="gauge-left">
                <span class="gauge-score">{score}</span>
                <span class="gauge-scale">/ 10.0</span>
              </div>
              <div class="gauge-info">
                <strong class="gauge-label">{entity.severity || 'CVSS SEVERITY'}</strong>
                {#if entity.metrics?.cvss_vector || entity.details?.['CVSS Vector']}
                  <code class="gauge-vector">{entity.metrics?.cvss_vector || entity.details?.['CVSS Vector']}</code>
                {/if}
              </div>
            </div>
          {/if}
        {/if}

        {#if entity.summary}
          <div class="drawer-section">
            <h3 class="section-heading"><span class="heading-icon">📖</span> {i18n.summary || 'Summary'}</h3>
            <p class="summary-text">{entity.summary}</p>
          </div>
        {/if}

        <!-- Windows Event Specific Tactical Forensic Guidance -->
        {#if (entity.type || '').toLowerCase() === 'winevent'}
          {#if entity.attributes?.['Investigation Tips'] || entity.details?.['Investigation Tips']}
            {@const tips = entity.attributes?.['Investigation Tips'] || entity.details?.['Investigation Tips']}
            <div class="tactical-box tactical-tips">
              <h4 class="tactical-heading">🔍 Forensic Investigation Playbook</h4>
              <ul class="tactical-list">
                {#each splitPipeList(tips) as tip}
                  <li>{tip}</li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if entity.attributes?.['Attacker Behavior'] || entity.details?.['Attacker Behavior']}
            {@const behavior = entity.attributes?.['Attacker Behavior'] || entity.details?.['Attacker Behavior']}
            <div class="tactical-box tactical-threat">
              <h4 class="tactical-heading">⚡ Adversary Tactics & Techniques</h4>
              <ul class="tactical-list">
                {#each splitPipeList(behavior) as item}
                  <li>{item}</li>
                {/each}
              </ul>
            </div>
          {/if}
        {/if}

        <!-- EVTX Log File Tactical Guidance -->
        {#if (entity.type || '').toLowerCase() === 'evtx'}
          {#if entity.details?.['Forensic Role'] || entity.attributes?.['Audit Recommendation']}
            <div class="tactical-box tactical-telemetry">
              <h4 class="tactical-heading">🗄️ Forensic Channel Telemetry</h4>
              {#if entity.details?.['Forensic Role']}
                <p class="tactical-desc">{entity.details['Forensic Role']}</p>
              {/if}
              {#if entity.attributes?.['Channel Path']}
                <div class="tactical-path">
                  <span class="path-label">Default Log Path:</span>
                  <code>{entity.attributes['Channel Path']}</code>
                </div>
              {/if}
            </div>
          {/if}
        {/if}

        <!-- CWE Specific Top 25 Banner & Tactical Defense Playbook -->
        {#if (entity.type || '').toLowerCase() === 'cwe'}
          {#if entity.classification?.top25_rank}
            <div class="cwe-rank-badge">
              <span class="rank-trophy">🏆</span>
              <div class="rank-meta">
                <strong>MITRE CWE TOP 25 MOST DANGEROUS WEAKNESSES</strong>
                <span class="rank-position">OFFICIAL RANK #{entity.classification.top25_rank}</span>
              </div>
            </div>
          {/if}

          {#if entity.details?.['Common Consequences']}
            <div class="tactical-box tactical-threat">
              <h4 class="tactical-heading">💥 Technical Impact & Consequences</h4>
              <ul class="tactical-list">
                {#each splitPipeList(entity.details['Common Consequences']) as impact}
                  <li>{impact}</li>
                {/each}
              </ul>
            </div>
          {/if}

          {#if entity.details?.['Mitigation Strategy']}
            <div class="tactical-box tactical-tips">
              <h4 class="tactical-heading">🛡️ Defensive Remediation & Mitigations</h4>
              <ul class="tactical-list">
                {#each splitPipeList(entity.details['Mitigation Strategy']) as mit}
                  <li>{mit}</li>
                {/each}
              </ul>
            </div>
          {/if}
        {/if}

        <!-- IP Address Network Scope & Threat Intelligence -->
        {#if (entity.type || '').toLowerCase() === 'ip'}
          <div class="tactical-box tactical-telemetry">
            <h4 class="tactical-heading">🌐 Network Endpoint Classification</h4>
            {#if entity.details?.['Network Scope']}
              <div class="tactical-path">
                <span class="path-label">Scope:</span>
                <code>{entity.details['Network Scope']}</code>
              </div>
            {/if}
            {#if entity.details?.['Organization'] && entity.details['Organization'] !== 'Internal Infrastructure'}
              <div class="tactical-path">
                <span class="path-label">Organization:</span>
                <strong>{entity.details['Organization']}</strong>
                {#if entity.details?.['Autonomous System (ASN)']}
                  <span class="muted-asn">({entity.details['Autonomous System (ASN)']})</span>
                {/if}
              </div>
            {/if}
            {#if entity.details?.['Open Ports'] && entity.details['Open Ports'] !== 'None scanned'}
              <div class="tactical-path">
                <span class="path-label">Open Ports (Shodan):</span>
                <code>{entity.details['Open Ports']}</code>
              </div>
            {/if}
            {#if entity.details?.['Reverse DNS (PTR)'] && entity.details['Reverse DNS (PTR)'] !== 'None resolved'}
              <div class="tactical-path">
                <span class="path-label">Reverse DNS:</span>
                <code>{entity.details['Reverse DNS (PTR)']}</code>
              </div>
            {/if}
          </div>
        {/if}

        <!-- Cryptographic Hash & VirusTotal Threat Intelligence -->
        {#if (entity.type || '').toLowerCase() === 'hash'}
          <div class="tactical-box tactical-threat">
            <h4 class="tactical-heading">#️⃣ Cryptographic Hash & Threat Intelligence</h4>
            {#if entity.details?.['Algorithm']}
              <div class="tactical-path">
                <span class="path-label">Algorithm:</span>
                <strong>{entity.details['Algorithm']}</strong> ({entity.details['Bit Length'] || ''})
              </div>
            {/if}
            {#if entity.details?.['Detection Ratio'] && entity.details['Detection Ratio'] !== 'Unchecked'}
              <div class="tactical-path">
                <span class="path-label">VirusTotal Detection:</span>
                <span class="vt-ratio-badge">{entity.details['Detection Ratio']}</span>
              </div>
            {/if}
            {#if entity.details?.['Identified Threat Label'] && entity.details['Identified Threat Label'] !== 'None assigned'}
              <div class="tactical-path">
                <span class="path-label">Threat Classification:</span>
                <code>{entity.details['Identified Threat Label']}</code>
              </div>
            {/if}
            {#if entity.details?.['Security Status']}
              <p class="tactical-desc">Status: {entity.details['Security Status']}</p>
            {/if}
          </div>
        {/if}

        <!-- Metrics & CVSS Grid -->
        {#if entity.metrics && Object.keys(entity.metrics).length > 0}
          <div class="drawer-section">
            <h3 class="section-heading"><span class="heading-icon">📊</span> {i18n.metrics || 'Telemetry & Scoring Metrics'}</h3>
            <div class="metrics-grid">
              {#each Object.entries(entity.metrics) as [key, val]}
                <div class="metric-card">
                  <span class="metric-key">{key.replace(/_/g, ' ').toUpperCase()}</span>
                  <span class="metric-val">{val}</span>
                </div>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Classification & TTPs -->
        {#if entity.classification && Object.keys(entity.classification).length > 0}
          <div class="drawer-section">
            <h3 class="section-heading"><span class="heading-icon">🎯</span> {i18n.classification || 'Classification & TTPs'}</h3>
            <div class="ttp-tags">
              {#each Object.entries(entity.classification) as [k, val]}
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

        <!-- Related Entities & Pivot Graph -->
        {#if entity.relationships && entity.relationships.length > 0}
          <div class="drawer-section">
            <h3 class="section-heading"><span class="heading-icon">🔗</span> {i18n.relationships || 'Pivot Telemetry & Lateral Links'}</h3>
            <div class="relationship-chips">
              {#each entity.relationships as rel}
                <button
                  class="rel-chip type-{(rel.type || 'entity').toLowerCase()}"
                  on:click={() => selectRelatedTarget(rel.target)}
                  title="Pivot to {rel.target}"
                >
                  <span class="rel-icon">{getTypeIcon(rel.type)}</span>
                  <span class="rel-badge">{rel.relation?.replace(/_/g, ' ') || 'relates to'}</span>
                  <span class="rel-target">{rel.target} ↗</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Core Attributes & Metadata (Excluding already-featured tips) -->
        {#if entity.attributes && Object.keys(entity.attributes).length > 0}
          {@const filteredAttrs = Object.entries(entity.attributes).filter(([k]) => k !== 'Investigation Tips' && k !== 'Attacker Behavior' && k !== 'Forensic Role')}
          {#if filteredAttrs.length > 0}
            <div class="drawer-section">
              <h3 class="section-heading"><span class="heading-icon">📋</span> {i18n.attributes || 'Key Attributes'}</h3>
              <table class="attributes-table">
                <tbody>
                  {#each filteredAttrs as [key, val]}
                    <tr>
                      <th scope="row">{key}</th>
                      <td>
                        {#if typeof val === 'string' && isTargetResolvable(val)}
                          <button class="inline-pivot-btn" on:click={() => selectRelatedTarget(val)} title="Inspect {val}">
                            {val} ↗
                          </button>
                        {:else}
                          {val}
                        {/if}
                      </td>
                    </tr>
                  {/each}
                </tbody>
              </table>
            </div>
          {/if}
        {/if}

        <!-- Technical Details Table -->
        {#if entity.details && Object.keys(entity.details).length > 0}
          {@const filteredDetails = Object.entries(entity.details).filter(([k]) => k !== 'Investigation Tips' && k !== 'Attacker Behavior' && k !== 'Forensic Role')}
          {#if filteredDetails.length > 0}
            <div class="drawer-section">
              <h3 class="section-heading"><span class="heading-icon">⚙️</span> {i18n.details || 'Technical Details'}</h3>
              <table class="attributes-table details-table">
                <tbody>
                  {#each filteredDetails as [key, val]}
                    <tr>
                      <th scope="row">{key}</th>
                      <td>
                        {#if typeof val === 'string' && isTargetResolvable(val)}
                          <button class="inline-pivot-btn" on:click={() => selectRelatedTarget(val)} title="Inspect {val}">
                            {val} ↗
                          </button>
                        {:else if key === 'Associated CVE' && typeof val === 'string' && val.startsWith('CVE-')}
                          <button class="inline-pivot-btn" on:click={() => selectRelatedTarget(val)} title="Inspect {val}">
                            🛡️ {val} ↗
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
        {/if}

        <!-- Verified External References -->
        {#if entity.references && entity.references.length > 0}
          <div class="drawer-section">
            <h3 class="section-heading"><span class="heading-icon">🌐</span> {i18n.references || 'Verified References'}</h3>
            <ul class="references-list">
              {#each entity.references as ref}
                <li>
                  <a href={ref.url} target="_blank" rel="noopener noreferrer">
                    {ref.title || ref.url} ↗
                  </a>
                </li>
              {/each}
            </ul>
          </div>
        {/if}

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

      {:else if activeTab === 'comments'}
        <!-- Review & Comments Tab View -->
        <div class="comments-management-view">
          <div class="export-actions-row">
            <button
              class="export-btn export-html-btn"
              on:click={() => exportUpdatedHtmlBundle($annotationStore.annotations, document.title)}
              title="Download standalone HTML report with comments embedded"
            >
              <Icon name="box" size={13} />
              <span>Export HTML Bundle</span>
            </button>
            <button
              class="export-btn export-md-btn"
              on:click={() => {
                const mdScript = document.getElementById('md-style-source-markdown');
                const rawMd = mdScript ? mdScript.textContent?.replace(/<\\\/script>/g, '<' + '/script>').trim() || '' : '';
                exportCriticMarkdown(rawMd, $annotationStore.annotations, document.title);
              }}
              title="Download source Markdown with CriticMarkup notes"
            >
              <Icon name="file-text" size={13} />
              <span>Export CriticMarkup .md</span>
            </button>
          </div>

          {#if $annotationStore.annotations.length > 0}
            <div class="comments-list">
              {#each $annotationStore.annotations as ann (ann.id)}
                <AnnotationCard
                  annotation={ann}
                  isActive={$annotationStore.activeAnnotationId === ann.id}
                  on:select={(e) => annotationStore.setActive(e.detail)}
                  on:update={(e) => annotationStore.updateAnnotation(e.detail.id, e.detail.text, e.detail.category)}
                  on:delete={(e) => annotationStore.deleteAnnotation(e.detail)}
                  on:toggleResolved={(e) => annotationStore.toggleResolved(e.detail)}
                />
              {/each}
            </div>
          {:else}
            <div class="empty-comments-notice">
              <span class="empty-icon"><Icon name="message-square" size={24} /></span>
              <p><strong>No comments yet</strong></p>
              <p class="empty-subtitle">Select any text in the document to attach comments, insights, corrections, or praise.</p>
            </div>
          {/if}
        </div>
      {:else}
        <!-- Catalog Browser View -->
        {#if hasSourceMarkdown}
          <div class="archive-action-card">
            <div class="archive-info">
              <span class="archive-icon"><Icon name="file-text" size={18} /></span>
              <div class="archive-text">
                <strong>Source Document Archive</strong>
                <span>Embedded raw Markdown archive</span>
              </div>
            </div>
            <button class="download-archive-btn" on:click={onDownloadSource} title="Download Markdown Source">
              <Icon name="file-text" size={13} />
              <span>Download .md</span>
            </button>
          </div>
        {/if}

        {#if entityList.length > 0}
          <!-- Search & Filter Controls -->
          <div class="search-box">
            <span class="search-icon"><Icon name="search" size={13} /></span>
            <input
              type="text"
              class="search-input"
              placeholder={i18n.filter_placeholder || 'Search knowledge entities...'}
              bind:value={searchQuery}
            />
            {#if searchQuery}
              <button class="search-clear-btn" on:click={() => (searchQuery = '')} aria-label="Clear search">
                <Icon name="x" size={12} />
              </button>
            {/if}
          </div>

          <!-- Category Pills -->
          <div class="category-pills">
            <button
              class="pill-btn"
              class:active={selectedCategory === 'all'}
              on:click={() => (selectedCategory = 'all')}
            >
              All ({entityList.length})
            </button>
            {#each Object.entries(categories) as [cat, count]}
              <button
                class="pill-btn"
                class:active={selectedCategory === cat}
                on:click={() => (selectedCategory = cat)}
              >
                {cat.toUpperCase()} ({count})
              </button>
            {/each}
          </div>

          <!-- Entity List -->
          <div class="entity-cards-list">
            {#each filteredEntities as item}
              <div
                class="entity-item-card"
                on:click={() => { entity = item; onSelectEntity(item); }}
                role="button"
                tabindex="0"
              >
                <div class="item-header">
                  <span class="item-id">{item.id}</span>
                  <span class="badge badge-{item.severity?.toLowerCase() || 'info'}">
                    {item.severity || 'INFO'}
                  </span>
                </div>
                {#if item.title && item.title !== item.id}
                  <div class="item-title">{item.title}</div>
                {/if}
                {#if item.summary}
                  <div class="item-summary">{item.summary}</div>
                {/if}
              </div>
            {/each}
            {#if filteredEntities.length === 0}
              <div class="no-results-msg">No entities matching your query.</div>
            {/if}
          </div>
        {:else}
          <div class="empty-kb-notice">
            <p>No knowledge base entities were identified in this document.</p>
          </div>
        {/if}
      {/if}
    </div>
  </aside>
{/if}

<style>
  .drawer-container {
    position: fixed;
    top: 40px;
    right: 0;
    height: calc(100vh - 40px);
    width: 440px;
    max-width: 90vw;
    background: rgba(15, 23, 42, 0.96);
    backdrop-filter: blur(12px);
    -webkit-backdrop-filter: blur(12px);
    color: #e2e8f0;
    border-left: 1px solid rgba(255, 255, 255, 0.12);
    box-shadow: -8px 0 24px rgba(0, 0, 0, 0.4);
    z-index: 9999;
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    font-family: var(--font-mono, "JetBrains Mono", "Cascadia Code", "Fira Code", monospace);
    animation: slideIn 0.22s cubic-bezier(0.16, 1, 0.3, 1);
  }
  @keyframes slideIn {
    from { transform: translateX(100%); }
    to { transform: translateX(0); }
  }
  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.15rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    background: rgba(15, 23, 42, 0.98);
    position: sticky;
    top: 0;
    z-index: 2;
  }
  .header-tab-bar {
    display: flex;
    gap: 0.35rem;
    align-items: center;
  }
  .header-tab-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.12);
    color: #94a3b8;
    padding: 0.25rem 0.55rem;
    border-radius: 4px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .header-tab-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.08);
  }
  .header-tab-btn.active {
    background: rgba(56, 189, 248, 0.18);
    border-color: #38bdf8;
    color: #38bdf8;
  }
  .comments-management-view {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    height: 100%;
  }
  .export-actions-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
  .export-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.45rem 0.6rem;
    font-size: 0.74rem;
    font-weight: 600;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    transition: background 0.15s ease;
    white-space: nowrap;
    text-align: center;
  }
  .export-html-btn {
    background: #0284c7;
    color: #fff;
  }
  .export-html-btn:hover { background: #0369a1; }
  .export-md-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #cbd5e1;
  }
  .export-md-btn:hover { background: rgba(255, 255, 255, 0.18); color: #fff; }
  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    overflow-y: auto;
  }
  .empty-comments-notice {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1.5rem;
    text-align: center;
    color: #94a3b8;
  }
  .empty-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .empty-subtitle { font-size: 0.78rem; color: #64748b; margin-top: 0.25rem; }

  .header-title-block {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }
  .header-icon {
    font-size: 1.1rem;
  }
  .header-title {
    font-size: 0.95rem;
    font-weight: 700;
    letter-spacing: -0.01em;
    color: #f8fafc;
  }
  .entity-subnav-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.5rem 1.15rem;
    background: rgba(15, 23, 42, 0.7);
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  }
  .nav-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #cbd5e1;
    font-size: 0.8rem;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .nav-back-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
  .header-badges {
    display: flex;
    gap: 0.5rem;
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
  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
  }
  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }
  .drawer-body {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    flex: 1;
  }
  .archive-action-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 0.85rem 1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 1rem;
  }
  .archive-info {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }
  .archive-icon {
    font-size: 1.3rem;
  }
  .archive-text {
    display: flex;
    flex-direction: column;
    font-size: 0.82rem;
  }
  .archive-text strong {
    color: #f1f5f9;
  }
  .archive-text span {
    color: #94a3b8;
    font-size: 0.75rem;
  }
  .download-archive-btn {
    background: #0284c7;
    color: #ffffff;
    border: none;
    font-size: 0.78rem;
    font-weight: 600;
    padding: 0.35rem 0.75rem;
    border-radius: 4px;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s ease;
  }
  .download-archive-btn:hover {
    background: #0369a1;
  }
  .search-box {
    position: relative;
    display: flex;
    align-items: center;
  }
  .search-icon {
    position: absolute;
    left: 10px;
    color: #64748b;
    display: flex;
    align-items: center;
    pointer-events: none;
  }
  .search-input {
    width: 100%;
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 5px;
    color: #f8fafc;
    padding: 0.5rem 0.75rem 0.5rem 2.1rem;
    font-size: 0.85rem;
    outline: none;
  }
  .search-input:focus {
    border-color: #38bdf8;
    box-shadow: 0 0 0 2px rgba(56, 189, 248, 0.2);
  }
  .search-clear-btn {
    position: absolute;
    right: 8px;
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 4px;
    border-radius: 4px;
  }
  .search-clear-btn:hover {
    color: #fff;
    background: rgba(255, 255, 255, 0.1);
  }
  .category-pills {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .pill-btn {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #94a3b8;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.55rem;
    border-radius: 12px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .pill-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #fff;
  }
  .pill-btn.active {
    background: #0284c7;
    border-color: #0284c7;
    color: #ffffff;
  }
  .entity-cards-list {
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    overflow-y: auto;
  }
  .entity-item-card {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 6px;
    padding: 0.75rem 0.9rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .entity-item-card:hover {
    border-color: #38bdf8;
    background: #24344d;
    transform: translateY(-1px);
  }
  .item-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.3rem;
  }
  .item-id {
    font-family: monospace;
    font-size: 0.82rem;
    color: #38bdf8;
    font-weight: 600;
  }
  .item-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #f1f5f9;
    margin-bottom: 0.25rem;
  }
  .item-summary {
    font-size: 0.78rem;
    color: #94a3b8;
    line-height: 1.4;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  .no-results-msg, .empty-kb-notice {
    font-size: 0.85rem;
    color: #64748b;
    text-align: center;
    padding: 1.5rem 0;
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

  .cvss-hero-gauge {
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
  }
  .cvss-hero-gauge.cvss-critical {
    background: rgba(239, 68, 68, 0.12);
    border-color: rgba(239, 68, 68, 0.35);
  }
  .cvss-hero-gauge.cvss-high {
    background: rgba(249, 115, 22, 0.12);
    border-color: rgba(249, 115, 22, 0.35);
  }
  .gauge-left {
    display: flex;
    align-items: baseline;
    gap: 0.2rem;
  }
  .gauge-score {
    font-size: 1.6rem;
    font-weight: 800;
    font-family: var(--font-mono, monospace);
    color: #ef4444;
    line-height: 1;
  }
  .cvss-high .gauge-score { color: #f97316; }
  .cvss-medium .gauge-score { color: #eab308; }
  .cvss-info .gauge-score { color: #38bdf8; }
  .gauge-scale {
    font-size: 0.75rem;
    color: #94a3b8;
    font-weight: 600;
  }
  .gauge-info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    overflow: hidden;
  }
  .gauge-label {
    font-size: 0.75rem;
    letter-spacing: 0.05em;
    color: #f1f5f9;
  }
  .gauge-vector {
    font-size: 0.68rem;
    color: #94a3b8;
    font-family: var(--font-mono, monospace);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .cwe-rank-badge {
    display: flex;
    align-items: center;
    gap: 0.85rem;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
  }
  .rank-trophy {
    font-size: 1.6rem;
  }
  .rank-meta {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .rank-meta strong {
    font-size: 0.72rem;
    color: #fbbf24;
    letter-spacing: 0.05em;
    text-transform: uppercase;
  }
  .rank-position {
    font-size: 0.88rem;
    font-weight: 800;
    color: #ffffff;
    font-family: var(--font-mono, monospace);
  }

  .tactical-box {
    border-radius: 6px;
    padding: 0.85rem 1rem;
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .tactical-tips {
    background: rgba(14, 165, 233, 0.08);
    border-color: rgba(14, 165, 233, 0.25);
  }
  .tactical-threat {
    background: rgba(239, 68, 68, 0.08);
    border-color: rgba(239, 68, 68, 0.25);
  }
  .tactical-telemetry {
    background: rgba(168, 85, 247, 0.08);
    border-color: rgba(168, 85, 247, 0.25);
  }
  .tactical-heading {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.04em;
    margin: 0 0 0.5rem 0;
    color: #f1f5f9;
  }
  .tactical-tips .tactical-heading { color: #38bdf8; }
  .tactical-threat .tactical-heading { color: #f87171; }
  .tactical-telemetry .tactical-heading { color: #c084fc; }
  .tactical-list {
    margin: 0;
    padding-left: 1.15rem;
    font-size: 0.82rem;
    line-height: 1.55;
    color: #cbd5e1;
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .tactical-desc {
    font-size: 0.82rem;
    line-height: 1.5;
    color: #cbd5e1;
    margin: 0 0 0.5rem 0;
  }
  .tactical-path {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.75rem;
  }
  .path-label {
    color: #94a3b8;
  }
  .tactical-path code {
    background: rgba(0, 0, 0, 0.25);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    color: #c084fc;
    font-size: 0.72rem;
  }

  .section-heading {
    display: flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin: 0 0 0.5rem 0;
  }
  .heading-icon {
    font-size: 0.9rem;
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
  .drawer-section h3 {
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    color: #94a3b8;
    margin: 0 0 0.5rem 0;
  }
  .summary-text {
    font-size: 0.88rem;
    line-height: 1.55;
    margin: 0;
    color: #cbd5e1;
  }
  .attributes-table {
    width: 100%;
    border-collapse: collapse;
    font-size: 0.82rem;
  }
  .attributes-table th, .attributes-table td {
    padding: 0.4rem 0.5rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.06);
    text-align: left;
  }
  .attributes-table th {
    color: #94a3b8;
    width: 35%;
  }
  .attributes-table td {
    color: #cbd5e1;
  }
  .references-list {
    margin: 0;
    padding-left: 1.25rem;
    font-size: 0.85rem;
  }
  .references-list a {
    color: #38bdf8;
    text-decoration: none;
  }
  .references-list a:hover {
    text-decoration: underline;
  }
  .metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
    gap: 0.5rem;
  }
  .metric-card {
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 4px;
    padding: 0.45rem 0.6rem;
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
  }
  .metric-key {
    font-size: 0.68rem;
    color: #94a3b8;
    font-weight: 700;
    letter-spacing: 0.05em;
  }
  .metric-val {
    font-family: monospace;
    font-size: 0.85rem;
    color: #38bdf8;
    font-weight: 700;
    word-break: break-all;
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
  }
  .tag-label {
    color: #94a3b8;
    text-transform: capitalize;
  }
  .relationship-chips {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
  }
  .rel-chip {
    background: #1e293b;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 4px;
    padding: 0.25rem 0.55rem;
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .rel-chip:hover {
    background: #0284c7;
    border-color: #38bdf8;
  }
  .rel-badge {
    font-size: 0.68rem;
    color: #94a3b8;
    text-transform: uppercase;
  }
  .rel-chip:hover .rel-badge {
    color: #e0f2fe;
  }
  .rel-target {
    font-family: monospace;
    font-size: 0.78rem;
    color: #38bdf8;
    font-weight: 600;
  }
  .rel-chip:hover .rel-target {
    color: #ffffff;
  }
  .details-table th {
    width: 40%;
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
  .drawer-footer {
    margin-top: auto;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.06);
  }
  .provenance-stamp {
    font-size: 0.72rem;
    color: #64748b;
  }

  /* --------------------------------------------------------------------------
     Light Mode Unification
     -------------------------------------------------------------------------- */
  :global([data-theme="light"]) .drawer-container,
  :global(body.light-theme) .drawer-container,
  :global(body.theme-forensic-dossier) .drawer-container {
    background: rgba(255, 255, 255, 0.98);
    color: #1e293b;
    border-left: 1px solid #cbd5e1;
    box-shadow: -8px 0 24px rgba(15, 23, 42, 0.08);
  }
  :global([data-theme="light"]) .drawer-header,
  :global(body.light-theme) .drawer-header,
  :global(body.theme-forensic-dossier) .drawer-header {
    background: rgba(248, 250, 252, 0.98);
    border-bottom: 1px solid #e2e8f0;
  }
  :global([data-theme="light"]) .entity-subnav-bar,
  :global(body.light-theme) .entity-subnav-bar,
  :global(body.theme-forensic-dossier) .entity-subnav-bar {
    background: rgba(241, 245, 249, 0.95);
    border-bottom: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .header-tab-btn,
  :global(body.light-theme) .header-tab-btn,
  :global(body.theme-forensic-dossier) .header-tab-btn {
    border-color: rgba(0, 0, 0, 0.12);
    color: #64748b;
  }
  :global([data-theme="light"]) .header-tab-btn:hover,
  :global(body.light-theme) .header-tab-btn:hover,
  :global(body.theme-forensic-dossier) .header-tab-btn:hover {
    color: #0f172a;
    background: rgba(0, 0, 0, 0.05);
  }
  :global([data-theme="light"]) .header-tab-btn.active,
  :global(body.light-theme) .header-tab-btn.active,
  :global(body.theme-forensic-dossier) .header-tab-btn.active {
    background: rgba(2, 132, 199, 0.1);
    border-color: #0284c7;
    color: #0284c7;
  }
  :global([data-theme="light"]) .nav-back-btn,
  :global(body.light-theme) .nav-back-btn,
  :global(body.theme-forensic-dossier) .nav-back-btn {
    border-color: rgba(0, 0, 0, 0.15);
    color: #475569;
  }
  :global([data-theme="light"]) .nav-back-btn:hover,
  :global(body.light-theme) .nav-back-btn:hover,
  :global(body.theme-forensic-dossier) .nav-back-btn:hover {
    background: rgba(0, 0, 0, 0.06);
    color: #0f172a;
  }
  :global([data-theme="light"]) .export-md-btn,
  :global(body.light-theme) .export-md-btn,
  :global(body.theme-forensic-dossier) .export-md-btn {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #334155;
  }
  :global([data-theme="light"]) .export-md-btn:hover,
  :global(body.light-theme) .export-md-btn:hover,
  :global(body.theme-forensic-dossier) .export-md-btn:hover {
    background: #e2e8f0;
    color: #0f172a;
  }
  :global([data-theme="light"]) .header-title,
  :global([data-theme="light"]) .entity-title,
  :global(body.light-theme) .header-title,
  :global(body.light-theme) .entity-title,
  :global(body.theme-forensic-dossier) .header-title,
  :global(body.theme-forensic-dossier) .entity-title {
    color: #0f172a;
  }
  :global([data-theme="light"]) .entity-item-card,
  :global([data-theme="light"]) .archive-action-card,
  :global(body.light-theme) .entity-item-card,
  :global(body.light-theme) .archive-action-card {
    background: #f8fafc;
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .entity-item-card:hover,
  :global(body.light-theme) .entity-item-card:hover {
    background: #f1f5f9;
    border-color: #0284c7;
  }
  :global([data-theme="light"]) .item-title,
  :global(body.light-theme) .item-title {
    color: #0f172a;
  }
  :global([data-theme="light"]) .search-input,
  :global(body.light-theme) .search-input {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.15);
    color: #0f172a;
  }
  :global([data-theme="light"]) .pill-btn,
  :global(body.light-theme) .pill-btn {
    background: rgba(0, 0, 0, 0.04);
    border: 1px solid rgba(0, 0, 0, 0.1);
    color: #475569;
  }
  :global([data-theme="light"]) .pill-btn:hover,
  :global(body.light-theme) .pill-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #0f172a;
  }
  :global([data-theme="light"]) .pill-btn.active,
  :global(body.light-theme) .pill-btn.active {
    background: #0284c7;
    color: #ffffff;
  }
  :global([data-theme="light"]) .summary-text,
  :global([data-theme="light"]) .attributes-table td,
  :global(body.light-theme) .summary-text,
  :global(body.light-theme) .attributes-table td {
    color: #334155;
  }
  :global([data-theme="light"]) .attributes-table th,
  :global([data-theme="light"]) .metric-key,
  :global([data-theme="light"]) .drawer-section h3,
  :global(body.light-theme) .attributes-table th,
  :global(body.light-theme) .metric-key,
  :global(body.light-theme) .drawer-section h3 {
    color: #64748b;
  }
  :global([data-theme="light"]) .metric-card,
  :global(body.light-theme) .metric-card {
    background: #f8fafc;
    border: 1px solid rgba(0, 0, 0, 0.06);
  }
  :global([data-theme="light"]) .rel-chip,
  :global(body.light-theme) .rel-chip {
    background: #f1f5f9;
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .rel-chip:hover,
  :global(body.light-theme) .rel-chip:hover {
    background: #0284c7;
    border-color: #0284c7;
  }
  :global([data-theme="light"]) .entity-id,
  :global(body.light-theme) .entity-id {
    background: rgba(0, 0, 0, 0.05);
    color: #0284c7;
  }
  :global([data-theme="light"]) .entity-hero-card,
  :global(body.light-theme) .entity-hero-card {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  }
  :global([data-theme="light"]) .cvss-hero-gauge,
  :global(body.light-theme) .cvss-hero-gauge {
    background: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .gauge-label,
  :global(body.light-theme) .gauge-label {
    color: #0f172a;
  }
  :global([data-theme="light"]) .tactical-tips,
  :global(body.light-theme) .tactical-tips {
    background: #f0f9ff;
    border-color: #bae6fd;
  }
  :global([data-theme="light"]) .tactical-threat,
  :global(body.light-theme) .tactical-threat {
    background: #fef2f2;
    border-color: #fecaca;
  }
  :global([data-theme="light"]) .tactical-telemetry,
  :global(body.light-theme) .tactical-telemetry {
    background: #faf5ff;
    border-color: #e9d5ff;
  }
  :global([data-theme="light"]) .tactical-list,
  :global([data-theme="light"]) .tactical-desc,
  :global(body.light-theme) .tactical-list,
  :global(body.light-theme) .tactical-desc {
    color: #334155;
  }
  :global([data-theme="light"]) .inline-pivot-btn,
  :global(body.light-theme) .inline-pivot-btn {
    background: rgba(2, 132, 199, 0.08);
    border: 1px solid rgba(2, 132, 199, 0.25);
    color: #0284c7;
  }
  :global([data-theme="light"]) .inline-pivot-btn:hover,
  :global(body.light-theme) .inline-pivot-btn:hover {
    background: #0284c7;
    color: #ffffff;
  }
  :global([data-theme="light"]) .badge-transitive,
  :global(body.light-theme) .badge-transitive {
    background: rgba(147, 51, 234, 0.1);
    color: #7e22ce;
    border: 1px solid rgba(147, 51, 234, 0.3);
  }
  :global([data-theme="light"]) .cwe-rank-badge,
  :global(body.light-theme) .cwe-rank-badge {
    background: #fffbeb;
    border-color: #fde68a;
  }
  :global([data-theme="light"]) .rank-meta strong,
  :global(body.light-theme) .rank-meta strong {
    color: #b45309;
  }
  :global([data-theme="light"]) .rank-position,
  :global(body.light-theme) .rank-position {
    color: #92400e;
  }
</style>
