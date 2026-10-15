<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import CvssGauge from '../../components/widgets/CvssGauge.svelte';
  import TacticalBox from '../../components/widgets/TacticalBox.svelte';
  import RankTrophy from '../../components/widgets/RankTrophy.svelte';
  import PivotChips from '../../components/widgets/PivotChips.svelte';
  import AttributesTable from '../../components/widgets/AttributesTable.svelte';
  import SummarySection from '../../components/widgets/SummarySection.svelte';
  import MetricsGrid from '../../components/widgets/MetricsGrid.svelte';
  import ClassificationTags from '../../components/widgets/ClassificationTags.svelte';
  import ReferencesList from '../../components/widgets/ReferencesList.svelte';
  import QRPlatbaWidget from '../../components/widgets/QRPlatbaWidget.svelte';

  export let entity: any;
  export let allEntities: Record<string, any> = {};
  export let checkResolvable: ((t: string) => boolean) | null = null;
  export let i18n: Record<string, string> = {};

  const dispatch = createEventDispatcher<{
    pivot: string;
  }>();

  $: widgets = Array.isArray(entity?.widgets) ? entity.widgets : [];
  $: hasPivotsWidget = widgets.some((w: any) => w.widget_type === 'pivots');
  $: hasAttributesWidget = widgets.some((w: any) => w.widget_type === 'attributes_table' || w.widget_type === 'kv_grid');
</script>

<div class="family-card dynamic-schema-card">
  <!-- 1. Render custom widgets defined in schema if present -->
  {#if widgets.length > 0}
    {#each widgets as w}
      {#if w.widget_type === 'gauge'}
        <CvssGauge
          score={w.data?.score ?? 0}
          severity={w.data?.severity || 'CVSS SEVERITY'}
          vector={w.data?.vector || ''}
        />
      {:else if w.widget_type === 'tactical_box'}
        <TacticalBox
          title={w.title}
          tone={w.tone || 'info'}
          description={w.data?.description || ''}
          code={w.data?.code || ''}
          codeLabel={w.data?.codeLabel || ''}
          items={w.items || []}
        />
      {:else if w.widget_type === 'rank_badge'}
        <RankTrophy
          title={w.title || 'RANKING BADGE'}
          rank={w.data?.rank || 1}
        />
      {:else if w.widget_type === 'pivots'}
        <PivotChips
          relationships={w.data?.relationships || entity.relationships}
          title={w.title || i18n.relationships || 'Pivot Telemetry & Lateral Links'}
          on:pivot={(e) => dispatch('pivot', e.detail)}
        />
      {:else if w.widget_type === 'attributes_table' || w.widget_type === 'kv_grid'}
        <AttributesTable
          data={w.data?.data || entity.attributes}
          title={w.title || i18n.attributes || 'Key Attributes'}
          isDetailsTable={w.data?.isDetailsTable || false}
          icon={w.data?.icon || 'file-text'}
          {allEntities}
          {checkResolvable}
          on:pivot={(e) => dispatch('pivot', e.detail)}
        />
      {:else if w.widget_type === 'qr_platba'}
        <QRPlatbaWidget
          account={w.data?.account || ''}
          iban={w.data?.iban || ''}
          bankName={w.data?.bank_name || ''}
          bankCode={w.data?.bank_code || ''}
          bic={w.data?.bic || ''}
          spayd={w.data?.spayd || ''}
          amount={w.data?.amount || null}
          vs={w.data?.vs || ''}
        />
      {/if}
    {/each}
  {/if}

  <!-- 2. Standard Fallback Sections -->
  <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />

  <MetricsGrid metrics={entity.metrics} title={i18n.metrics || 'Telemetry & Scoring Metrics'} />

  <ClassificationTags classification={entity.classification} title={i18n.classification || 'Classification & TTPs'} />

  {#if !hasPivotsWidget}
    <PivotChips
      relationships={entity.relationships}
      title={i18n.relationships || 'Pivot Telemetry & Lateral Links'}
      on:pivot={(e) => dispatch('pivot', e.detail)}
    />
  {/if}

  {#if !hasAttributesWidget}
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
  {/if}

  <ReferencesList references={entity.references} title={i18n.references || 'Verified References'} />
</div>

<style>
  .family-card {
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
</style>
