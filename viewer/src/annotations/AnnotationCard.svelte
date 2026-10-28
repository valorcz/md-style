<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { DocumentAnnotation, AnnotationCategory } from './types';
  import { renderAnnotationMarkdown } from './markdown';
  import Icon from '../components/Icon.svelte';

  export let annotation: DocumentAnnotation;
  export let isActive: boolean = false;
  export let compact: boolean = false;

  const dispatch = createEventDispatcher<{
    select: string;
    update: { id: string; text: string; category?: AnnotationCategory };
    delete: string;
    toggleResolved: string;
  }>();

  let isEditing = false;
  let editText = annotation.text;
  let editCategory = annotation.category;

  const categoryMeta: Record<AnnotationCategory, { label: string; icon: string; color: string }> = {
    feedback: { label: 'Comment', icon: 'message-square', color: '#1a73e8' },
    correction: { label: 'Correction', icon: 'alert-circle', color: '#ea4335' },
    insight: { label: 'Insight', icon: 'lightbulb', color: '#f9ab00' },
    commendation: { label: 'Praise', icon: 'award', color: '#34a853' },
    question: { label: 'Question', icon: 'help-circle', color: '#a142f4' }
  };

  $: authorInitials = (annotation.author || 'R')
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map(p => p[0].toUpperCase())
    .join('') || 'R';

  function handleSaveEdit() {
    if (!editText.trim()) return;
    dispatch('update', { id: annotation.id, text: editText.trim(), category: editCategory });
    isEditing = false;
  }

  function handleCardClick() {
    if (isEditing) return;
    dispatch('select', annotation.id);
  }

  function handleCardKeyDown(e: KeyboardEvent) {
    if (isEditing) return;
    if (e.key === 'Enter' || e.key === ' ') {
      const target = e.target as HTMLElement;
      if (target.tagName === 'BUTTON' || target.tagName === 'TEXTAREA' || target.tagName === 'A') {
        return;
      }
      e.preventDefault();
      dispatch('select', annotation.id);
    }
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<!-- svelte-ignore a11y_no_noninteractive_tabindex -->
<div
  class="annotation-card category-{annotation.category}"
  class:active={isActive}
  class:resolved={annotation.resolved}
  class:compact={compact}
  on:click={handleCardClick}
  on:keydown={handleCardKeyDown}
  role="article"
  tabindex="0"
>
  <!-- Card Header -->
  <div class="card-header">
    <div class="header-left">
      <div class="card-avatar" title={annotation.author}>{authorInitials}</div>
      <div class="author-details">
        <span class="card-author">{annotation.author}</span>
        <span class="category-badge" style="--badge-color: {categoryMeta[annotation.category]?.color || '#1a73e8'}">
          <Icon name={categoryMeta[annotation.category]?.icon || 'message-square'} size={11} />
          {categoryMeta[annotation.category]?.label}
        </span>
      </div>
    </div>
    <div class="header-actions">
      <button
        class="action-icon-btn resolve-btn"
        class:is-resolved={annotation.resolved}
        on:click|stopPropagation={() => dispatch('toggleResolved', annotation.id)}
        title={annotation.resolved ? 'Mark as Unresolved' : 'Mark as Resolved'}
        aria-label={annotation.resolved ? 'Mark as Unresolved' : 'Mark as Resolved'}
      >
        <Icon name={annotation.resolved ? 'rotate-ccw' : 'check'} size={13} />
      </button>
      <button
        class="action-icon-btn edit-btn"
        on:click|stopPropagation={() => (isEditing = !isEditing)}
        title="Edit note"
        aria-label="Edit note"
      >
        <Icon name="pencil" size={12} />
      </button>
      <button
        class="action-icon-btn delete-btn"
        on:click|stopPropagation={() => dispatch('delete', annotation.id)}
        title="Delete note"
        aria-label="Delete note"
      >
        <Icon name="trash" size={12} />
      </button>
    </div>
  </div>

  <!-- Context Quote (Google Docs style) -->
  {#if annotation.range?.quote}
    <div class="card-quote">
      "{annotation.range.quote.length > 75 ? annotation.range.quote.slice(0, 75) + '…' : annotation.range.quote}"
    </div>
  {/if}

  {#if !isEditing}
    <div class="card-text markdown-body">
      {@html renderAnnotationMarkdown(annotation.text)}
    </div>
    <div class="card-footer">
      <span class="card-time">{new Date(annotation.createdAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
      {#if annotation.resolved}
        <span class="resolved-badge">
          <Icon name="check-circle" size={11} />
          RESOLVED
        </span>
      {/if}
    </div>
  {:else}
    <div class="card-edit-box">
      <textarea class="edit-textarea" bind:value={editText} rows="2"></textarea>
      <div class="edit-actions">
        <button class="btn-sm-cancel" on:click={() => (isEditing = false)}>Cancel</button>
        <button class="btn-sm-save" on:click={handleSaveEdit}>Save</button>
      </div>
    </div>
  {/if}
</div>

<style>
  .annotation-card {
    background: #ffffff;
    border: 1px solid #dadce0;
    border-left: 3px solid #1a73e8;
    border-radius: 8px;
    padding: 0.65rem 0.75rem;
    color: #1f2937;
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    font-size: 0.8rem;
    transition: all 0.15s cubic-bezier(0.16, 1, 0.3, 1);
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(60, 64, 67, 0.12), 0 1px 2px rgba(60, 64, 67, 0.24);
    box-sizing: border-box;
  }

  .annotation-card:hover {
    border-color: #bdc1c6;
    box-shadow: 0 2px 6px rgba(60, 64, 67, 0.15);
    transform: translateY(-1px);
  }

  .annotation-card.active {
    border-color: #1a73e8;
    border-left-width: 4px;
    box-shadow: 0 4px 14px rgba(26, 115, 232, 0.18), 0 1px 3px rgba(60, 64, 67, 0.12);
  }

  .annotation-card.category-correction { border-left-color: #ea4335; }
  .annotation-card.category-insight { border-left-color: #f9ab00; }
  .annotation-card.category-commendation { border-left-color: #34a853; }
  .annotation-card.category-question { border-left-color: #a142f4; }

  .annotation-card.resolved {
    opacity: 0.65;
    background: #f8f9fa;
    border-left-color: #9aa0a6;
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.4rem;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .card-avatar {
    width: 24px;
    height: 24px;
    border-radius: 50%;
    background: #e8f0fe;
    color: #1a73e8;
    font-size: 0.68rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 1px solid rgba(26, 115, 232, 0.2);
  }

  .author-details {
    display: flex;
    flex-direction: column;
    gap: 0.05rem;
  }

  .card-author {
    font-size: 0.78rem;
    font-weight: 600;
    color: #202124;
    line-height: 1.2;
  }

  .category-badge {
    font-size: 0.64rem;
    font-weight: 600;
    color: var(--badge-color, #1a73e8);
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    line-height: 1.1;
  }

  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.2rem;
  }

  .action-icon-btn {
    background: transparent;
    border: none;
    color: #5f6368;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 50%;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.12s ease;
  }

  .action-icon-btn:hover {
    color: #202124;
    background: rgba(0, 0, 0, 0.06);
  }

  .action-icon-btn.resolve-btn:hover {
    color: #137333;
    background: rgba(19, 115, 51, 0.1);
  }

  .action-icon-btn.delete-btn:hover {
    color: #d93025;
    background: rgba(217, 48, 37, 0.1);
  }

  .card-quote {
    font-size: 0.72rem;
    color: #5f6368;
    background: rgba(26, 115, 232, 0.04);
    padding: 0.3rem 0.5rem;
    border-radius: 0 4px 4px 0;
    border-left: 2px solid #1a73e8;
    margin-bottom: 0.45rem;
    font-style: italic;
    line-height: 1.35;
  }

  .card-text {
    line-height: 1.45;
    color: #3c4043;
    overflow-wrap: break-word;
    word-break: break-word;
    font-size: 0.8rem;
  }

  /* Scoped Markdown Formatting */
  :global(.card-text.markdown-body p) {
    margin: 0.25rem 0;
  }
  :global(.card-text.markdown-body p:first-child) {
    margin-top: 0;
  }
  :global(.card-text.markdown-body p:last-child) {
    margin-bottom: 0;
  }
  :global(.card-text.markdown-body pre) {
    background: #f1f3f4;
    border: 1px solid #dadce0;
    border-radius: 4px;
    padding: 0.35rem 0.5rem;
    font-size: 0.74rem;
    max-height: 160px;
    overflow-x: auto;
    overflow-y: auto;
    margin: 0.35rem 0;
  }
  :global(.card-text.markdown-body code) {
    font-family: var(--font-mono, monospace);
    font-size: 0.76rem;
    background: #f1f3f4;
    padding: 0.1rem 0.3rem;
    border-radius: 3px;
    color: #1a73e8;
  }
  :global(.card-text.markdown-body ul),
  :global(.card-text.markdown-body ol) {
    margin: 0.25rem 0;
    padding-left: 1.1rem;
    font-size: 0.78rem;
  }
  :global(.card-text.markdown-body li) {
    margin-bottom: 0.15rem;
  }
  :global(.card-text.markdown-body a) {
    color: #1a73e8;
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  :global(.card-text.markdown-body blockquote) {
    border-left: 2px solid #1a73e8;
    padding-left: 0.5rem;
    margin: 0.25rem 0;
    font-style: italic;
    color: #5f6368;
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.45rem;
    font-size: 0.68rem;
    color: #80868b;
  }

  .resolved-badge {
    font-weight: 700;
    color: #188038;
    letter-spacing: 0.04em;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    background: #e6f4ea;
    padding: 0.1rem 0.4rem;
    border-radius: 10px;
  }

  .card-edit-box {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-top: 0.4rem;
  }

  .edit-textarea {
    width: 100%;
    box-sizing: border-box;
    background: #ffffff;
    border: 1px solid #1a73e8;
    color: #202124;
    border-radius: 4px;
    padding: 0.4rem;
    font-size: 0.78rem;
    font-family: inherit;
    outline: none;
    box-shadow: 0 0 0 2px rgba(26, 115, 232, 0.2);
  }

  .edit-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.35rem;
  }

  .btn-sm-cancel {
    background: transparent;
    border: none;
    color: #5f6368;
    font-size: 0.72rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-sm-cancel:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .btn-sm-save {
    background: #1a73e8;
    border: none;
    color: #ffffff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.65rem;
    border-radius: 4px;
    cursor: pointer;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  }

  .btn-sm-save:hover {
    background: #1557b0;
  }

  /* --------------------------------------------------------------------------
     Dark Mode
     -------------------------------------------------------------------------- */
  :global([data-theme="dark"]) .annotation-card,
  :global(body.dark-theme) .annotation-card {
    background: #1e293b;
    border-color: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
  }

  :global([data-theme="dark"]) .annotation-card:hover,
  :global(body.dark-theme) .annotation-card:hover {
    border-color: rgba(255, 255, 255, 0.2);
  }

  :global([data-theme="dark"]) .annotation-card.active,
  :global(body.dark-theme) .annotation-card.active {
    border-color: #38bdf8;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.25);
  }

  :global([data-theme="dark"]) .card-avatar,
  :global(body.dark-theme) .card-avatar {
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border-color: rgba(56, 189, 248, 0.3);
  }

  :global([data-theme="dark"]) .card-author,
  :global(body.dark-theme) .card-author {
    color: #f1f5f9;
  }

  :global([data-theme="dark"]) .action-icon-btn,
  :global(body.dark-theme) .action-icon-btn {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .action-icon-btn:hover,
  :global(body.dark-theme) .action-icon-btn:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.1);
  }

  :global([data-theme="dark"]) .card-quote,
  :global(body.dark-theme) .card-quote {
    background: rgba(0, 0, 0, 0.3);
    color: #94a3b8;
    border-left-color: #38bdf8;
  }

  :global([data-theme="dark"]) .card-text,
  :global(body.dark-theme) .card-text {
    color: #f1f5f9;
  }

  :global([data-theme="dark"] .card-text.markdown-body pre),
  :global(body.dark-theme .card-text.markdown-body pre) {
    background: rgba(0, 0, 0, 0.5);
    border-color: rgba(255, 255, 255, 0.1);
  }

  :global([data-theme="dark"] .card-text.markdown-body code),
  :global(body.dark-theme .card-text.markdown-body code) {
    background: rgba(255, 255, 255, 0.1);
    color: #38bdf8;
  }

  :global([data-theme="dark"]) .edit-textarea,
  :global(body.dark-theme) .edit-textarea {
    background: rgba(15, 23, 42, 0.8);
    border-color: #38bdf8;
    color: #fff;
  }

  :global([data-theme="dark"]) .btn-sm-cancel,
  :global(body.dark-theme) .btn-sm-cancel {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .btn-sm-save,
  :global(body.dark-theme) .btn-sm-save {
    background: #0284c7;
  }
</style>
