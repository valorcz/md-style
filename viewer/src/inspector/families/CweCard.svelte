<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import RankTrophy from '../../components/widgets/RankTrophy.svelte';
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

  $: top25Rank = entity?.classification?.top25_rank;
  $: consequences = entity?.details?.['Common Consequences'];
  $: mitigations = entity?.details?.['Mitigation Strategy'];
</script>

<div class="family-card cwe-family-card">
  {#if top25Rank}
    <RankTrophy rank={top25Rank} />
  {/if}

  <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />

  {#if consequences}
    <TacticalBox
      tone="threat"
      title="Technical Impact & Consequences"
      icon="alert-circle"
      items={splitPipeList(consequences)}
    />
  {/if}

  {#if mitigations}
    <TacticalBox
      tone="defense"
      title="Defensive Remediation & Mitigations"
      icon="academic"
      items={splitPipeList(mitigations)}
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
