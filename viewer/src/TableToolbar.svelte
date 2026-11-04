<script lang="ts">
  import { onMount } from 'svelte';
  import Icon from './components/Icon.svelte';
  import PillButton from './components/ui/PillButton.svelte';
  import IconButton from './components/ui/IconButton.svelte';
  import Badge from './components/ui/Badge.svelte';

  export let tableElement: HTMLTableElement;
  export let i18n: Record<string, string> = {};

  let query: string = '';
  let totalRows: number = 0;
  let visibleRows: number = 0;

  interface CategoryPill {
    name: string;
    count: number;
  }
  let categoryColumnIdx: number = -1;
  let categoryPills: CategoryPill[] = [];
  let selectedCategory: string = 'ALL';

  function initTableStats() {
    if (!tableElement) return;
    const tbody = tableElement.querySelector('tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    totalRows = rows.length;
    visibleRows = totalRows;

    // Auto-discover categorical column with 2 to 5 recurring values
    if (rows.length >= 4) {
      const numCols = rows[0]?.children.length || 0;
      for (let col = 0; col < numCols; col++) {
        const counts: Record<string, number> = {};
        let isValid = true;
        for (const row of rows) {
          const cell = row.children[col];
          if (!cell) { isValid = false; break; }
          const val = cell.textContent?.trim().replace(/\s+/g, ' ') || '';
          if (val.length === 0 || val.length > 30) { isValid = false; break; }
          counts[val] = (counts[val] || 0) + 1;
        }
        if (!isValid) continue;

        const uniqueVals = Object.keys(counts);
        if (uniqueVals.length >= 2 && uniqueVals.length <= 5 && uniqueVals.length < rows.length) {
          categoryColumnIdx = col;
          categoryPills = uniqueVals.map(name => ({ name, count: counts[name] }));
          break;
        }
      }
    }
  }

  function applyFilter() {
    if (!tableElement) return;
    const tbody = tableElement.querySelector('tbody');
    if (!tbody) return;
    const rows = Array.from(tbody.querySelectorAll('tr'));
    const q = query.trim().toLowerCase();
    let count = 0;

    rows.forEach(row => {
      let matchesCategory = true;
      if (categoryColumnIdx >= 0 && selectedCategory !== 'ALL') {
        const cellVal = row.children[categoryColumnIdx]?.textContent?.trim() || '';
        matchesCategory = cellVal.toLowerCase() === selectedCategory.toLowerCase();
      }

      let matchesQuery = true;
      if (q) {
        const rowText = row.textContent?.toLowerCase() || '';
        matchesQuery = rowText.includes(q);
      }

      if (matchesCategory && matchesQuery) {
        row.style.display = '';
        count++;
      } else {
        row.style.display = 'none';
      }
    });

    visibleRows = count;
  }

  function selectCategory(cat: string) {
    selectedCategory = cat;
    applyFilter();
  }

  function clearQuery() {
    query = '';
    applyFilter();
  }

  onMount(() => {
    initTableStats();
  });
</script>

<div class="table-toolbar" aria-label="Table filter controls">
  <div class="toolbar-left">
    {#if categoryPills.length > 0}
      <div class="category-pills">
        <PillButton
          class="pill-btn"
          active={selectedCategory === 'ALL'}
          on:click={() => selectCategory('ALL')}
        >
          {i18n['ui.all_categories'] || 'All'} ({totalRows})
        </PillButton>
        {#each categoryPills as pill}
          <PillButton
            class="pill-btn"
            active={selectedCategory === pill.name}
            on:click={() => selectCategory(pill.name)}
          >
            {pill.name} ({pill.count})
          </PillButton>
        {/each}
      </div>
    {/if}
    <div class="search-box">
      <span class="search-icon"><Icon name="search" size={13} /></span>
      <input
        type="text"
        placeholder={i18n['ui.filter_placeholder'] || 'Filter table records...'}
        bind:value={query}
        on:input={applyFilter}
        aria-label="Filter rows"
      />
      {#if query}
        <IconButton
          class="clear-btn"
          name="x"
          size={12}
          title="Clear filter"
          ariaLabel="Clear filter"
          on:click={clearQuery}
        />
      {/if}
    </div>
  </div>
  <div class="toolbar-right">
    <Badge class="count-badge" variant="subtle" size="sm">{visibleRows} / {totalRows}</Badge>
  </div>
</div>

<style>
  .table-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.45rem 0.75rem;
    background: rgba(15, 23, 42, 0.05);
    border: 1px solid var(--color-border, #e2e8f0);
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 0.8rem;
    gap: 0.75rem;
    flex-wrap: wrap;
  }
  .toolbar-left {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex-wrap: wrap;
    flex: 1;
  }
  .category-pills {
    display: flex;
    align-items: center;
    gap: 0.35rem;
  }
  :global(.clear-btn) {
    position: absolute;
    right: 2px;
  }
  @media print {
    .table-toolbar {
      display: none !important;
    }
    :global(tr[style*="display: none"]) {
      display: table-row !important;
    }
  }
</style>
