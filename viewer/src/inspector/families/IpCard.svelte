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

<div class="family-card ip-family-card">
  <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />

  <TacticalBox
    tone="telemetry"
    title="Network Endpoint Classification"
    icon="layout"
  >
    {#if details['Network Scope']}
      <div class="tactical-path">
        <span class="path-label">Scope:</span>
        <code>{details['Network Scope']}</code>
      </div>
    {/if}
    {#if details['Organization'] && details['Organization'] !== 'Internal Infrastructure'}
      <div class="tactical-path">
        <span class="path-label">Organization:</span>
        <strong>{details['Organization']}</strong>
        {#if details['Autonomous System (ASN)']}
          <span class="muted-asn">({details['Autonomous System (ASN)']})</span>
        {/if}
      </div>
    {/if}
    {#if details['Open Ports'] && details['Open Ports'] !== 'None scanned'}
      <div class="tactical-path">
        <span class="path-label">Open Ports (Shodan):</span>
        <code>{details['Open Ports']}</code>
      </div>
    {/if}
    {#if details['Reverse DNS (PTR)'] && details['Reverse DNS (PTR)'] !== 'None resolved'}
      <div class="tactical-path">
        <span class="path-label">Reverse DNS:</span>
        <code>{details['Reverse DNS (PTR)']}</code>
      </div>
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
    color: #38bdf8;
  }
  .muted-asn {
    font-size: 0.8rem;
    color: #94a3b8;
    margin-left: 0.25rem;
  }

  :global([data-theme="light"]) .tactical-path code,
  :global(body.theme-forensic-dossier) .tactical-path code {
    background: #f1f5f9;
    border-color: #cbd5e1;
    color: #0369a1;
  }
  :global([data-theme="light"]) .path-label,
  :global(body.theme-forensic-dossier) .path-label {
    color: #64748b;
  }
  :global([data-theme="light"]) .muted-asn,
  :global(body.theme-forensic-dossier) .muted-asn {
    color: #64748b;
  }
</style>
