<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../components/Icon.svelte';

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
        on:click={() => dispatch('tab', 'kb')}
      >
        <Icon name="layers" size={13} />
        <span>{i18n.knowledge_inspector || 'Entities'} ({entityCount})</span>
      </button>
      <button
        class="header-tab-btn"
        class:active={activeTab === 'comments'}
        on:click={() => dispatch('tab', 'comments')}
      >
        <Icon name="message-square" size={13} />
        <span>Review ({commentsCount})</span>
      </button>
    </div>
  {/if}
  <button class="close-btn" on:click={() => dispatch('close')} aria-label={i18n.close || 'Close'}>
    <Icon name="x" size={15} />
  </button>
</header>

<style>
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
  .close-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    font-size: 1.1rem;
    cursor: pointer;
    padding: 0.25rem 0.5rem;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
  }
  .close-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #fff;
  }

  /* Light Theme */
  :global([data-theme="light"]) .drawer-header,
  :global(body.light-theme) .drawer-header,
  :global(body.theme-forensic-dossier) .drawer-header {
    background: rgba(248, 250, 252, 0.98);
    border-bottom: 1px solid #e2e8f0;
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
</style>
