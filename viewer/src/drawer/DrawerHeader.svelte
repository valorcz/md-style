<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';
  import IconButton from '../components/ui/IconButton.svelte';

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
    <button class="nav-back-btn" on:click={() => dispatch('back')}>
      <Icon name="chevron-left" size={13} />
      <span>{i18n.all_entities || 'All Entities'}</span>
    </button>
  {:else}
    <div class="header-tab-bar">
      <button
        class="header-tab-btn"
        class:active={activeTab === 'kb'}
        on:click={() => dispatch('tab', 'kb')}
      >
        <Icon name="layers" size={13} />
        <span>{i18n.entities || 'Entities'} ({entityCount})</span>
      </button>
      <button
        class="header-tab-btn"
        class:active={activeTab === 'comments'}
        on:click={() => dispatch('tab', 'comments')}
      >
        <Icon name="message-square" size={13} />
        <span>{i18n.review || 'Review'} ({commentsCount})</span>
      </button>
    </div>
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
    border: 1px solid var(--color-border, #e2e8f0);
    color: var(--color-text-muted, #64748b);
    padding: 0.25rem 0.55rem;
    border-radius: 4px;
    font-size: 0.76rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .header-tab-btn:hover {
    color: var(--color-text, #0f172a);
    background: rgba(0, 0, 0, 0.04);
  }
  .header-tab-btn.active {
    background: rgba(37, 99, 235, 0.08);
    border-color: var(--color-accent, #2563eb);
    color: var(--color-accent, #2563eb);
  }
  .nav-back-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    background: transparent;
    border: 1px solid var(--color-border, #e2e8f0);
    color: var(--color-text-muted, #475569);
    font-size: 0.8rem;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.15s ease;
  }
  .nav-back-btn:hover {
    background: rgba(0, 0, 0, 0.04);
    color: var(--color-text, #0f172a);
  }


  /* Dark Theme */
  :global([data-theme="dark"]) .drawer-header {
    background: #1a1b1f;
    border-bottom-color: #262930;
  }
  :global([data-theme="dark"]) .header-tab-btn,
  :global([data-theme="dark"]) .nav-back-btn {
    border-color: #262930;
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .header-tab-btn:hover,
  :global([data-theme="dark"]) .nav-back-btn:hover {
    color: #f1f5f9;
    background: rgba(255, 255, 255, 0.06);
  }
  :global([data-theme="dark"]) .header-tab-btn.active {
    background: rgba(96, 165, 250, 0.12);
    border-color: #60a5fa;
    color: #60a5fa;
  }
  
</style>
