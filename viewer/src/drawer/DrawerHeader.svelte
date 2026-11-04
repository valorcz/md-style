<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import IconButton from '../components/ui/IconButton.svelte';
  import SegmentedControl from '../components/ui/SegmentedControl.svelte';
  import Button from '../components/ui/Button.svelte';

  export let activeTab: 'kb' | 'comments' = 'kb';
  export let entity: any = null;
  export let entityCount: number = 0;
  export let commentsCount: number = 0;
  export let i18n: Record<string, string> = {};

  const dispatch = createEventDispatcher<{
    back: void;
    tab: 'kb' | 'comments';
    close: void;
  }>();
</script>

<header class="drawer-header">
  {#if activeTab === 'kb' && entity}
    <Button
      class="nav-back-btn"
      variant="secondary"
      icon="chevron-left"
      size="sm"
      on:click={() => dispatch('back')}
    >
      {i18n.all_entities || 'All Entities'}
    </Button>
  {:else}
    <SegmentedControl
      class="header-tab-bar"
      itemClass="header-tab-btn"
      options={[
        { id: 'kb', label: `${i18n.entities || 'Entities'} (${entityCount})`, icon: 'layers' },
        { id: 'comments', label: `${i18n.review || 'Review'} (${commentsCount})`, icon: 'message-square' }
      ]}
      value={activeTab}
      on:change={(e) => dispatch('tab', e.detail as 'kb' | 'comments')}
    />
  {/if}
  <IconButton
    class="close-btn"
    name="x"
    size={14}
    title={i18n.close || 'Close'}
    ariaLabel={i18n.close || 'Close'}
    on:click={() => dispatch('close')}
  />
</header>

<style>
  .drawer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.75rem 1.15rem;
    border-bottom: 1px solid var(--color-border, #e2e8f0);
    background: var(--color-paper, #ffffff);
    position: sticky;
    top: 0;
    z-index: 2;
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .drawer-header {
    background: #1a1b1f;
    border-bottom-color: #262930;
  }
</style>
