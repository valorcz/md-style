<script lang="ts">
  import { createEventDispatcher, onMount } from 'svelte';
  import type { AnnotationCategory } from './types';
  import { renderAnnotationMarkdown } from './markdown';
  import Icon from '../components/Icon.svelte';

  export let position: { x: number; y: number } = { x: 0, y: 0 };
  export let quoteText: string = '';

  const dispatch = createEventDispatcher<{
    create: { category: AnnotationCategory; text: string; author: string };
    cancel: void;
  }>();

  let isComposing = false;
  let showPreview = false;
  let selectedCategory: AnnotationCategory = 'feedback';
  let commentText = '';
  let authorName = 'Reviewer';
  let isDesktop = true;

  const categories: { id: AnnotationCategory; label: string; icon: string; color: string }[] = [
    { id: 'feedback', label: 'Comment', icon: 'message-square', color: '#1a73e8' },
    { id: 'correction', label: 'Correction', icon: 'alert-circle', color: '#ea4335' },
    { id: 'insight', label: 'Insight', icon: 'lightbulb', color: '#f9ab00' },
    { id: 'commendation', label: 'Praise', icon: 'award', color: '#34a853' },
    { id: 'question', label: 'Question', icon: 'help-circle', color: '#a142f4' }
  ];

  $: authorInitials = (authorName || 'R')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0].toUpperCase())
    .join('') || 'R';

  function checkViewport() {
    isDesktop = window.innerWidth >= 1100;
  }

  onMount(() => {
    checkViewport();
    window.addEventListener('resize', checkViewport);
    return () => window.removeEventListener('resize', checkViewport);
  });

  function startCompose(cat: AnnotationCategory) {
    selectedCategory = cat;
    isComposing = true;
  }

  function handleSave() {
    if (!commentText.trim()) return;
    dispatch('create', {
      category: selectedCategory,
      text: commentText.trim(),
      author: authorName.trim() || 'Reviewer'
    });
    isComposing = false;
    commentText = '';
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      dispatch('cancel');
    } else if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
      handleSave();
    }
  }

  function getDockLeft(): number {
    const root = document.querySelector('.report-content') || document.querySelector('main') || document.body;
    if (root) {
      const docRect = root.getBoundingClientRect();
      const idealLeft = docRect.right + 24;
      if (idealLeft + 280 <= window.innerWidth - 16) {
        return idealLeft;
      }
    }
    return Math.max(16, window.innerWidth - 304);
  }

  $: popoverTop = isComposing && isDesktop
    ? Math.max(48, Math.min(window.innerHeight - 340, position.y))
    : (position.y > 90 ? position.y - 46 : position.y + 26);

  $: popoverLeft = isComposing && isDesktop
    ? `${getDockLeft()}px`
    : `${Math.max(16, Math.min(window.innerWidth - 440, position.x - 200))}px`;

  $: popoverRight = 'auto';

  $: popoverWidth = isComposing && isDesktop
    ? '280px'
    : 'max-content';
</script>

<svelte:window on:keydown={handleKeydown} />

<div
  class="annotation-popover"
  class:docked-right={isComposing && isDesktop}
  class:composer-mode={isComposing}
  style="top: {popoverTop}px; left: {popoverLeft}; right: {popoverRight}; width: {popoverWidth};"
  role="dialog"
  aria-label="Add annotation to selection"
>
  {#if !isComposing}
    <div class="popover-action-bar">
      {#each categories as cat}
        <button
          class="popover-btn category-{cat.id}"
          style="--btn-color: {cat.color};"
          on:click={() => startCompose(cat.id)}
          title="Add {cat.label}"
        >
          <span class="btn-icon">
            <Icon name={cat.icon} size={14} />
          </span>
          <span class="btn-label">{cat.label}</span>
        </button>
      {/each}
      <button class="popover-close-btn" on:click={() => dispatch('cancel')} title="Cancel" aria-label="Cancel">
        <Icon name="x" size={13} />
      </button>
    </div>
  {:else}
    <div class="popover-composer">
      <!-- Google Docs-style Header -->
      <div class="composer-header">
        <div class="author-info">
          <div class="author-avatar" title={authorName}>{authorInitials}</div>
          <div class="author-meta">
            <input
              type="text"
              class="author-input"
              bind:value={authorName}
              placeholder="Your Name"
              title="Reviewer Name"
            />
            <span class="composer-category-tag" style="--cat-color: {categories.find(c => c.id === selectedCategory)?.color || '#1a73e8'}">
              <Icon name={categories.find(c => c.id === selectedCategory)?.icon || 'message-square'} size={12} />
              {categories.find(c => c.id === selectedCategory)?.label}
            </span>
          </div>
        </div>
        <div class="composer-mode-bar">
          <button class="mode-tab-btn" class:active={!showPreview} on:click={() => (showPreview = false)}>Write</button>
          <button class="mode-tab-btn" class:active={showPreview} on:click={() => (showPreview = true)} disabled={!commentText.trim()}>Preview</button>
        </div>
      </div>

      {#if quoteText}
        <div class="composer-quote">
          "{quoteText.length > 85 ? quoteText.slice(0, 85) + '…' : quoteText}"
        </div>
      {/if}

      {#if !showPreview}
        <textarea
          class="composer-textarea"
          bind:value={commentText}
          placeholder="Add a comment... (Markdown supported, Ctrl+Enter to save)"
          rows="3"
        ></textarea>
      {:else}
        <div class="composer-preview markdown-body">
          {@html renderAnnotationMarkdown(commentText)}
        </div>
      {/if}

      <div class="composer-footer">
        <!-- Category switcher pills -->
        <div class="composer-category-chips">
          {#each categories as cat}
            <button
              type="button"
              class="cat-chip"
              class:selected={selectedCategory === cat.id}
              style="--chip-color: {cat.color};"
              on:click={() => (selectedCategory = cat.id)}
              title="Switch to {cat.label}"
            >
              <Icon name={cat.icon} size={12} />
            </button>
          {/each}
        </div>
        <div class="composer-actions">
          <button class="btn-cancel" on:click={() => (isComposing = false)}>Cancel</button>
          <button class="btn-save" on:click={handleSave} disabled={!commentText.trim()}>Comment</button>
        </div>
      </div>
    </div>
  {/if}
</div>

<style>
  .annotation-popover {
    position: fixed;
    z-index: 10002;
    background: #ffffff;
    color: #1f2937;
    border: 1px solid #dadce0;
    border-radius: 8px;
    box-shadow: 0 2px 12px rgba(60, 64, 67, 0.18), 0 1px 3px rgba(60, 64, 67, 0.12);
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    animation: popIn 0.16s cubic-bezier(0.16, 1, 0.3, 1);
    max-width: calc(100vw - 32px);
    box-sizing: border-box;
  }

  .annotation-popover.composer-mode {
    width: 280px;
    max-width: 280px;
  }

  @keyframes popIn {
    from { opacity: 0; transform: translateY(-4px) scale(0.97); }
    to { opacity: 1; transform: translateY(0) scale(1); }
  }

  /* Compact Trigger Bar */
  .popover-action-bar {
    display: flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.3rem 0.4rem;
    background: inherit;
    border-radius: inherit;
  }

  .popover-btn {
    background: transparent;
    border: none;
    color: #4b5563;
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.35rem 0.55rem;
    border-radius: 6px;
    font-size: 0.76rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .popover-btn .btn-icon {
    display: inline-flex;
    align-items: center;
    color: var(--btn-color, #1a73e8);
  }

  .popover-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #111827;
  }

  .popover-close-btn {
    background: transparent;
    border: none;
    color: #9ca3af;
    padding: 0.3rem;
    cursor: pointer;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-left: auto;
  }

  .popover-close-btn:hover {
    color: #4b5563;
    background: rgba(0, 0, 0, 0.05);
  }

  /* Google Docs Style Composer */
  .popover-composer {
    width: 280px;
    box-sizing: border-box;
    padding: 0.75rem;
    display: flex;
    flex-direction: column;
    gap: 0.55rem;
  }

  .composer-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .author-info {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .author-avatar {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 0.7rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 1px solid rgba(26, 115, 232, 0.2);
  }

  .author-meta {
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
  }

  .author-input {
    background: transparent;
    border: none;
    border-bottom: 1px dotted rgba(0, 0, 0, 0.2);
    color: #1f2937;
    font-size: 0.75rem;
    font-weight: 600;
    padding: 0 0 1px 0;
    width: 90px;
    outline: none;
  }

  .author-input:focus {
    border-bottom-color: #1a73e8;
  }

  .composer-category-tag {
    font-size: 0.65rem;
    font-weight: 600;
    color: var(--cat-color, #1a73e8);
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
  }

  .composer-mode-bar {
    display: flex;
    background: rgba(0, 0, 0, 0.05);
    padding: 2px;
    border-radius: 5px;
  }

  .mode-tab-btn {
    background: transparent;
    border: none;
    color: #6b7280;
    font-size: 0.68rem;
    font-weight: 600;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .mode-tab-btn.active {
    background: #ffffff;
    color: #1f2937;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.08);
  }

  .mode-tab-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  /* Quoted context callout */
  .composer-quote {
    font-size: 0.72rem;
    color: #4b5563;
    background: rgba(26, 115, 232, 0.05);
    padding: 0.35rem 0.55rem;
    border-radius: 0 4px 4px 0;
    border-left: 2px solid #1a73e8;
    font-style: italic;
    line-height: 1.35;
  }

  .composer-textarea {
    width: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border: 1px solid #dadce0;
    border-radius: 6px;
    color: #1f2937;
    padding: 0.45rem 0.55rem;
    font-size: 0.78rem;
    font-family: inherit;
    line-height: 1.4;
    resize: vertical;
    outline: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }

  .composer-textarea:focus {
    border-color: #1a73e8;
    box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
  }

  .composer-preview {
    min-height: 58px;
    max-height: 140px;
    overflow-y: auto;
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 6px;
    padding: 0.45rem 0.55rem;
    font-size: 0.78rem;
    line-height: 1.4;
    color: #1f2937;
  }

  .composer-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.5rem;
    margin-top: 0.1rem;
  }

  .composer-category-chips {
    display: flex;
    gap: 0.2rem;
    align-items: center;
  }

  .cat-chip {
    background: transparent;
    border: 1px solid transparent;
    color: #9ca3af;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    transition: all 0.12s ease;
  }

  .cat-chip:hover {
    color: var(--chip-color, #1a73e8);
    background: rgba(0, 0, 0, 0.04);
  }

  .cat-chip.selected {
    color: var(--chip-color, #1a73e8);
    border-color: var(--chip-color, #1a73e8);
    background: rgba(26, 115, 232, 0.08);
  }

  .composer-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-left: auto;
  }

  .btn-cancel {
    background: transparent;
    border: none;
    color: #5f6368;
    padding: 0.3rem 0.6rem;
    border-radius: 4px;
    font-size: 0.75rem;
    font-weight: 500;
    cursor: pointer;
  }

  .btn-cancel:hover {
    background: rgba(0, 0, 0, 0.05);
    color: #202124;
  }

  .btn-save {
    background: #1a73e8;
    border: none;
    color: #ffffff;
    font-weight: 600;
    padding: 0.35rem 0.8rem;
    border-radius: 4px;
    font-size: 0.75rem;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.12);
    transition: background 0.15s ease, box-shadow 0.15s ease;
  }

  .btn-save:hover:not(:disabled) {
    background: #1557b0;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
  }

  .btn-save:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    background: #8ab4f8;
  }

  /* --------------------------------------------------------------------------
     Dark Mode
     -------------------------------------------------------------------------- */
  :global([data-theme="dark"]) .annotation-popover,
  :global(body.dark-theme) .annotation-popover {
    background: #1e293b;
    color: #f1f5f9;
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.45);
  }

  :global([data-theme="dark"]) .popover-btn,
  :global(body.dark-theme) .popover-btn {
    color: #cbd5e1;
  }

  :global([data-theme="dark"]) .popover-btn:hover,
  :global(body.dark-theme) .popover-btn:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
  }

  :global([data-theme="dark"]) .author-avatar,
  :global(body.dark-theme) .author-avatar {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 0.3);
  }

  :global([data-theme="dark"]) .author-input,
  :global(body.dark-theme) .author-input {
    color: #f1f5f9;
    border-bottom-color: rgba(255, 255, 255, 0.2);
  }

  :global([data-theme="dark"]) .composer-mode-bar,
  :global(body.dark-theme) .composer-mode-bar {
    background: rgba(255, 255, 255, 0.06);
  }

  :global([data-theme="dark"]) .mode-tab-btn.active,
  :global(body.dark-theme) .mode-tab-btn.active {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
  }

  :global([data-theme="dark"]) .composer-quote,
  :global(body.dark-theme) .composer-quote {
    background: rgba(56, 189, 248, 0.08);
    border-left-color: #38bdf8;
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .composer-textarea,
  :global(body.dark-theme) .composer-textarea {
    background: rgba(15, 23, 42, 0.6);
    border-color: rgba(255, 255, 255, 0.15);
    color: #f8fafc;
  }

  :global([data-theme="dark"]) .composer-preview,
  :global(body.dark-theme) .composer-preview {
    background: rgba(15, 23, 42, 0.4);
    border-color: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
  }

  :global([data-theme="dark"]) .btn-cancel,
  :global(body.dark-theme) .btn-cancel {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .btn-cancel:hover,
  :global(body.dark-theme) .btn-cancel:hover {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
  }

  :global([data-theme="dark"]) .btn-save,
  :global(body.dark-theme) .btn-save {
    background: #0284c7;
  }

  :global([data-theme="dark"]) .btn-save:hover:not(:disabled),
  :global(body.dark-theme) .btn-save:hover:not(:disabled) {
    background: #0369a1;
  }
</style>
