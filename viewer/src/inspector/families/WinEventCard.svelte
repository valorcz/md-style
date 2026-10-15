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

  function splitPipeList(val: string): string[] {
    if (!val || typeof val !== 'string') return [];
    return val.split('|').map(s => s.trim()).filter(Boolean);
  }

  $: tips = entity?.attributes?.['Investigation Tips'] || entity?.details?.['Investigation Tips'];
  $: behavior = entity?.attributes?.['Attacker Behavior'] || entity?.details?.['Attacker Behavior'];
</script>

<div class="family-card winevent-family-card">
  <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />

  {#if tips}
    <TacticalBox
      tone="defense"
      title="Forensic Investigation Playbook"
      icon="academic"
      items={splitPipeList(tips)}
    />
  {/if}

  {#if behavior}
    <TacticalBox
      tone="threat"
      title="Adversary Tactics & Techniques"
      icon="alert-circle"
      items={splitPipeList(behavior)}
    />
  {/if}

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
</style>
