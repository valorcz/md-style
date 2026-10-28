<script lang="ts">
  import { tick } from 'svelte';
  import { annotationStore } from './annotations/store';
  import DrawerHeader from './drawer/DrawerHeader.svelte';
  import EntitySearchFilter from './drawer/EntitySearchFilter.svelte';
  import EntityCardList from './drawer/EntityCardList.svelte';
  import EntityDetailView from './drawer/EntityDetailView.svelte';
  import CommentsAuditView from './drawer/CommentsAuditView.svelte';

  export let entity: any = null;
  export let isOpen: boolean = false;
  export let i18n: Record<string, string> = {};
  export let allEntities: Record<string, any> = {};
  export let hasSourceMarkdown: boolean = false;
  export let activeTab: 'kb' | 'comments' = 'kb';
  export let onClose: () => void = () => {};
  export let onSelectEntity: (e: any) => void = () => {};
  export let onDownloadSource: () => void = () => {};

  let searchQuery: string = '';
  let selectedCategory: string = 'all';
  let drawerContainer: HTMLElement | null = null;

  $: if (activeTab === 'comments' && $annotationStore.activeAnnotationId && drawerContainer) {
    tick().then(() => {
      const activeEl = drawerContainer?.querySelector('.annotation-card.is-active');
      if (activeEl) {
        activeEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    });
  }

  $: if (entity && drawerContainer) {
    drawerContainer.scrollTop = 0;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape' && isOpen) {
      onClose();
    }
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
</script>

<svelte:window on:keydown={handleKeydown} />

{#if isOpen}
  <aside bind:this={drawerContainer} class="drawer-container" aria-label="Entity Details Inspector">
    <DrawerHeader
      {activeTab}
      {entity}
      entityCount={entityList.length}
      commentsCount={$annotationStore.annotations.length}
      {i18n}
      on:back={() => { entity = null; }}
      on:tab={(e) => {
        activeTab = e.detail;
        if (e.detail === 'comments') entity = null;
      }}
      on:close={onClose}
    />

    <div class="drawer-body">
      {#if activeTab === 'kb' && entity}
        <EntityDetailView
          {entity}
          {allEntities}
          checkResolvable={isTargetResolvable}
          {i18n}
          on:pivot={(e) => selectRelatedTarget(e.detail)}
        />
      {:else if activeTab === 'comments'}
        <CommentsAuditView
          annotations={$annotationStore.annotations}
          activeAnnotationId={$annotationStore.activeAnnotationId}
        />
      {:else}
        <EntitySearchFilter
          bind:searchQuery
          bind:selectedCategory
          {categories}
          entityCount={entityList.length}
          {hasSourceMarkdown}
          {i18n}
          on:downloadSource={onDownloadSource}
        />
        <EntityCardList
          entities={filteredEntities}
          totalCount={entityList.length}
          on:select={(e) => {
            entity = e.detail;
            onSelectEntity(e.detail);
          }}
        />
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
  .drawer-body {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1.25rem;
    flex: 1;
  }

  /* Light Theme */
  :global([data-theme="light"]) .drawer-container,
  :global(body.light-theme) .drawer-container,
  :global(body.theme-forensic-dossier) .drawer-container {
    background: rgba(255, 255, 255, 0.98);
    color: #1e293b;
    border-left: 1px solid #cbd5e1;
    box-shadow: -8px 0 24px rgba(15, 23, 42, 0.08);
  }
</style>
