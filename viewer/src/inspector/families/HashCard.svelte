<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import TacticalBox from '../../components/widgets/TacticalBox.svelte';
  import SummarySection from '../../components/widgets/SummarySection.svelte';
  import MetricsGrid from '../../components/widgets/MetricsGrid.svelte';
  import ClassificationTags from '../../components/widgets/ClassificationTags.svelte';
  import PivotChips from '../../components/widgets/PivotChips.svelte';
  import AttributesTable from '../../components/widgets/AttributesTable.svelte';
  import ReferencesList from '../../components/widgets/ReferencesList.svelte';

  export let entity: any;
  export let allEntities: Record<string, any> = {};
  export let checkResolvable: ((t: string) => boolean) | null = null;
  export let i18n: Record<string, string> = {};

  const dispatch = createEventDispatcher<{
    pivot: string;
  }>();

  $: details = entity?.details || {};
</script>

<div class="family-card hash-family-card">
  <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />

  <TacticalBox
    tone="threat"
    title="Cryptographic Hash & Threat Intelligence"
    icon="alert-circle"
  >
    {#if details['Algorithm']}
      <div class="tactical-path">
        <span class="path-label">Algorithm:</span>
        <strong>{details['Algorithm']}</strong>
        {#if details['Bit Length']}
          <span class="muted-bits">({details['Bit Length']})</span>
        {/if}
      </div>
    {/if}
    {#if details['Detection Ratio'] && details['Detection Ratio'] !== 'Unchecked'}
      <div class="tactical-path">
        <span class="path-label">VirusTotal Detection:</span>
        <span class="vt-ratio-badge">{details['Detection Ratio']}</span>
      </div>
    {/if}
    {#if details['Identified Threat Label'] && details['Identified Threat Label'] !== 'None assigned'}
      <div class="tactical-path">
        <span class="path-label">Threat Classification:</span>
        <code>{details['Identified Threat Label']}</code>
      </div>
    {/if}
    {#if details['Security Status']}
      <p class="tactical-desc">Status: {details['Security Status']}</p>
    {/if}
  </TacticalBox>

  <MetricsGrid metrics={entity.metrics} title={i18n.metrics || 'Telemetry & Scoring Metrics'} />

  <ClassificationTags classification={entity.classification} title={i18n.classification || 'Classification & TTPs'} />

  <PivotChips
    relationships={entity.relationships}
    title={i18n.relationships || 'Pivot Telemetry & Lateral Links'}
    on:pivot={(e) => dispatch('pivot', e.detail)}
  />

  <AttributesTable
    data={entity.attributes}
    title={i18n.attributes || 'Key Attributes'}
    icon="file-text"
    {allEntities}
    {checkResolvable}
    on:pivot={(e) => dispatch('pivot', e.detail)}
  />

  <AttributesTable
    data={entity.details}
    title={i18n.details || 'Technical Details'}
    isDetailsTable={true}
    icon="settings"
    {allEntities}
    {checkResolvable}
    on:pivot={(e) => dispatch('pivot', e.detail)}
  />

  <ReferencesList references={entity.references} title={i18n.references || 'Verified References'} />
</div>

<style>
  .family-card {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .tactical-path {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    margin-top: 0.35rem;
    flex-wrap: wrap;
  }
  .path-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
  .tactical-path code {
    font-family: var(--font-mono, monospace);
    font-size: 0.82rem;
    background: rgba(0, 0, 0, 0.3);
    padding: 0.15rem 0.4rem;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.08);
    color: #f87171;
  }
  .muted-bits {
    font-size: 0.8rem;
    color: #94a3b8;
  }
  .vt-ratio-badge {
    display: inline-block;
    padding: 0.15rem 0.5rem;
    background: rgba(239, 68, 68, 0.2);
    border: 1px solid rgba(239, 68, 68, 0.4);
    color: #f87171;
    border-radius: 4px;
    font-size: 0.82rem;
    font-weight: 700;
    font-family: var(--font-mono, monospace);
  }
  .tactical-desc {
    margin: 0.5rem 0 0 0;
    font-size: 0.84rem;
    line-height: 1.45;
    color: #cbd5e1;
  }

  :global([data-theme="light"]) .tactical-path code,
  :global(body.theme-forensic-dossier) .tactical-path code {
    background: #fef2f2;
    border-color: #fecaca;
    color: #dc2626;
  }
  :global([data-theme="light"]) .vt-ratio-badge,
  :global(body.theme-forensic-dossier) .vt-ratio-badge {
    background: #fee2e2;
    border-color: #fca5a5;
    color: #b91c1c;
  }
  :global([data-theme="light"]) .path-label,
  :global(body.theme-forensic-dossier) .path-label {
    color: #64748b;
  }
  :global([data-theme="light"]) .tactical-desc,
  :global(body.theme-forensic-dossier) .tactical-desc {
    color: #334155;
  }
</style>
