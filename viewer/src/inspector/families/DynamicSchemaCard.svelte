<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { Accordion } from 'bits-ui';
  import Icon from '../../components/Icon.svelte';
  import Badge from '../../components/ui/Badge.svelte';
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
  $: hasSummaryInWidgets = widgets.some((w: any) => w.data?.description && w.data.description === entity.summary);
  $: resolvedReferences = (Array.isArray(entity?.references) && entity.references.length > 0)
    ? entity.references
    : (widgets.find((w: any) => w.widget_type === 'references')?.data?.references || []);

  // Section presence flags
  $: overviewWidgets = widgets.filter((w: any) => ['gauge', 'tactical_box', 'rank_badge'].includes(w.widget_type));
  $: hasOverviewSection = Boolean(
    overviewWidgets.length > 0 ||
    (!hasSummaryInWidgets && entity?.summary)
  );

  $: attributeWidgets = widgets.filter((w: any) => ['attributes_table', 'kv_grid', 'qr_platba'].includes(w.widget_type));
  $: attributesCount = (entity?.attributes ? Object.keys(entity.attributes).length : 0) +
    (entity?.details ? Object.keys(entity.details).length : 0) +
    (entity?.metrics ? Object.keys(entity.metrics).length : 0);
  $: hasAttributesSection = Boolean(
    attributeWidgets.length > 0 ||
    hasAttributesWidget ||
    attributesCount > 0 ||
    (entity?.classification && (Array.isArray(entity.classification) ? entity.classification.length > 0 : Object.keys(entity.classification).length > 0))
  );

  $: pivotsWidgets = widgets.filter((w: any) => w.widget_type === 'pivots');
  $: relationshipsList = entity?.relationships || [];
  $: relationshipsCount = Array.isArray(relationshipsList) ? relationshipsList.length : Object.keys(relationshipsList).length;
  $: hasPivotsSection = Boolean(
    pivotsWidgets.length > 0 ||
    hasPivotsWidget ||
    relationshipsCount > 0
  );

  $: hasReferencesSection = Boolean(resolvedReferences && resolvedReferences.length > 0);

  // Manage open accordion sections (all active open by default)
  let openSections: string[] = ['summary', 'attributes', 'pivots', 'references'];
</script>

<div class="family-card dynamic-schema-card">
  <Accordion.Root type="multiple" bind:value={openSections} class="accordion-root">
    <!-- 1. Overview Section -->
    {#if hasOverviewSection}
      <Accordion.Item value="summary" class="accordion-item">
        <Accordion.Header level={3} class="accordion-header">
          <Accordion.Trigger class="accordion-trigger">
            <div class="trigger-title-group">
              <span class="trigger-icon"><Icon name="file-text" size={14} /></span>
              <span class="trigger-label">{i18n.summary || 'Přehled a souhrn'}</span>
            </div>
            <span class="trigger-chevron"><Icon name="chevron-down" size={14} /></span>
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content class="accordion-content">
          <div class="section-body">
            {#each overviewWidgets as w}
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
                  icon={w.data?.icon || ''}
                  description={w.data?.description || ''}
                  code={w.data?.code || ''}
                  codeLabel={w.data?.codeLabel || ''}
                  items={w.items || w.data?.items || []}
                  fields={w.data?.fields || []}
                />
              {:else if w.widget_type === 'rank_badge'}
                <RankTrophy
                  title={w.title || 'RANKING BADGE'}
                  rank={w.data?.rank || 1}
                />
              {/if}
            {/each}

            {#if !hasSummaryInWidgets && entity.summary}
              <SummarySection summary={entity.summary} title={i18n.summary || 'Summary'} />
            {/if}
          </div>
        </Accordion.Content>
      </Accordion.Item>
    {/if}

    <!-- 2. Attributes & Metrics Section -->
    {#if hasAttributesSection}
      <Accordion.Item value="attributes" class="accordion-item">
        <Accordion.Header level={3} class="accordion-header">
          <Accordion.Trigger class="accordion-trigger">
            <div class="trigger-title-group">
              <span class="trigger-icon"><Icon name="sliders" size={14} /></span>
              <span class="trigger-label">{i18n.attributes || 'Vlastnosti & parametry'}</span>
              {#if attributesCount > 0}
                <Badge variant="subtle" size="sm">{attributesCount}</Badge>
              {/if}
            </div>
            <span class="trigger-chevron"><Icon name="chevron-down" size={14} /></span>
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content class="accordion-content">
          <div class="section-body">
            {#each attributeWidgets as w}
              {#if w.widget_type === 'attributes_table' || w.widget_type === 'kv_grid'}
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

            <MetricsGrid metrics={entity.metrics} title={i18n.metrics || 'Telemetry & Scoring Metrics'} />
            <ClassificationTags classification={entity.classification} title={i18n.classification || 'Classification & TTPs'} />

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
          </div>
        </Accordion.Content>
      </Accordion.Item>
    {/if}

    <!-- 3. Pivots & Relationships Section -->
    {#if hasPivotsSection}
      <Accordion.Item value="pivots" class="accordion-item">
        <Accordion.Header level={3} class="accordion-header">
          <Accordion.Trigger class="accordion-trigger">
            <div class="trigger-title-group">
              <span class="trigger-icon"><Icon name="layers" size={14} /></span>
              <span class="trigger-label">{i18n.relationships || 'Souvislosti & vazby'}</span>
              {#if relationshipsCount > 0}
                <Badge variant="subtle" size="sm">{relationshipsCount}</Badge>
              {/if}
            </div>
            <span class="trigger-chevron"><Icon name="chevron-down" size={14} /></span>
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content class="accordion-content">
          <div class="section-body">
            {#each pivotsWidgets as w}
              <PivotChips
                relationships={w.data?.relationships || entity.relationships}
                title={w.title || i18n.relationships || 'Pivot Telemetry & Lateral Links'}
                on:pivot={(e) => dispatch('pivot', e.detail)}
              />
            {/each}

            {#if !hasPivotsWidget}
              <PivotChips
                relationships={entity.relationships}
                title={i18n.relationships || 'Pivot Telemetry & Lateral Links'}
                on:pivot={(e) => dispatch('pivot', e.detail)}
              />
            {/if}
          </div>
        </Accordion.Content>
      </Accordion.Item>
    {/if}

    <!-- 4. References & Sources Section -->
    {#if hasReferencesSection}
      <Accordion.Item value="references" class="accordion-item">
        <Accordion.Header level={3} class="accordion-header">
          <Accordion.Trigger class="accordion-trigger">
            <div class="trigger-title-group">
              <span class="trigger-icon"><Icon name="external-link" size={14} /></span>
              <span class="trigger-label">{i18n.references || 'Zdroje & odkazy'}</span>
              <Badge variant="subtle" size="sm">{resolvedReferences.length}</Badge>
            </div>
            <span class="trigger-chevron"><Icon name="chevron-down" size={14} /></span>
          </Accordion.Trigger>
        </Accordion.Header>
        <Accordion.Content class="accordion-content">
          <div class="section-body">
            <ReferencesList references={resolvedReferences} title={i18n.references || 'Verified References'} />
          </div>
        </Accordion.Content>
      </Accordion.Item>
    {/if}
  </Accordion.Root>
</div>

<style>
  .family-card {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }

  :global(.accordion-root) {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    width: 100%;
  }

  :global(.accordion-item) {
    border: 1px solid var(--color-border, #e2e8f0);
    border-radius: 8px;
    background: var(--color-paper, #ffffff);
    overflow: hidden;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  :global(.accordion-header) {
    margin: 0;
    padding: 0;
  }

  :global(.accordion-trigger) {
    display: flex;
    width: 100%;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 0.95rem;
    background: transparent;
    border: none;
    font-family: inherit;
    font-size: 0.8rem;
    font-weight: 600;
    color: var(--color-primary, #0f172a);
    cursor: pointer;
    text-align: left;
    user-select: none;
    transition: background 0.15s ease;
  }

  :global(.accordion-trigger:hover) {
    background: rgba(0, 0, 0, 0.02);
  }

  :global(.trigger-title-group) {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  :global(.trigger-icon) {
    display: inline-flex;
    align-items: center;
    color: var(--color-accent, #2563eb);
  }

  :global(.trigger-chevron) {
    display: inline-flex;
    align-items: center;
    color: var(--color-text-muted, #64748b);
    transition: transform 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  :global(.accordion-trigger[data-state="open"] .trigger-chevron) {
    transform: rotate(180deg);
  }

  :global(.accordion-content) {
    padding: 0 0.95rem 0.95rem 0.95rem;
  }

  :global(.section-body) {
    display: flex;
    flex-direction: column;
    gap: 0.85rem;
    padding-top: 0.35rem;
    border-top: 1px solid var(--color-border, rgba(0, 0, 0, 0.05));
  }

  /* Dark Theme */
  :global([data-theme="dark"] .accordion-item) {
    background: #1e2024;
    border-color: #2e323b;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2);
  }
  :global([data-theme="dark"] .accordion-trigger) {
    color: #f1f5f9;
  }
  :global([data-theme="dark"] .accordion-trigger:hover) {
    background: rgba(255, 255, 255, 0.03);
  }
  :global([data-theme="dark"] .trigger-icon) {
    color: #60a5fa;
  }
  :global([data-theme="dark"] .trigger-chevron) {
    color: #94a3b8;
  }
  :global([data-theme="dark"] .section-body) {
    border-top-color: #262930;
  }
</style>
