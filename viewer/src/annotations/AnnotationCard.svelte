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
          <span class="category-dot" style="background-color: {categoryMeta[annotation.category]?.color || '#1a73e8'}"></span>
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
  /* --------------------------------------------------------------------------
     Clean Editorial & Paper Card Styling (Zero Visual Smog)
     -------------------------------------------------------------------------- */
  .annotation-card {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.08);
    border-radius: 8px;
    padding: 0.75rem 0.85rem;
    color: #1e293b;
    font-family: var(--font-sans, system-ui, -apple-system, sans-serif);
    font-size: 0.81rem;
    transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
    cursor: pointer;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
    box-sizing: border-box;
    position: relative;
  }

  .annotation-card:hover {
    border-color: rgba(0, 0, 0, 0.16);
    box-shadow: 0 4px 16px -2px rgba(0, 0, 0, 0.08);
    transform: translateY(-1px);
  }

  .annotation-card.active {
    border-color: #0284c7;
    box-shadow: 0 0 0 1px #0284c7, 0 6px 20px -2px rgba(2, 132, 199, 0.16);
  }

  .annotation-card.resolved {
    opacity: 0.55;
    background: #fafaf9;
    border-color: rgba(0, 0, 0, 0.05);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 0.45rem;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .card-avatar {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    background: #f1f5f9;
    color: #475569;
    font-size: 0.65rem;
    font-weight: 700;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 1px solid rgba(0, 0, 0, 0.06);
  }

  .author-details {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }

  .card-author {
    font-size: 0.78rem;
    font-weight: 600;
    color: #1e293b;
    line-height: 1.2;
  }

  .category-badge {
    font-size: 0.68rem;
    font-weight: 500;
    color: #64748b;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    line-height: 1.1;
  }

  .category-dot {
    width: 6px;
    height: 6px;
    border-radius: 50%;
    display: inline-block;
  }

  /* Quiet Header Actions: fade in on card hover/focus */
  .header-actions {
    display: flex;
    align-items: center;
    gap: 0.15rem;
    opacity: 0;
    transition: opacity 0.15s ease;
  }

  .annotation-card:hover .header-actions,
  .annotation-card.active .header-actions {
    opacity: 1;
  }

  .action-icon-btn {
    background: transparent;
    border: none;
    color: #94a3b8;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.12s ease;
  }

  .action-icon-btn:hover {
    color: #0f172a;
    background: rgba(0, 0, 0, 0.06);
  }

  .action-icon-btn.resolve-btn:hover {
    color: #10b981;
    background: rgba(16, 185, 129, 0.1);
  }

  .action-icon-btn.resolve-btn.is-resolved {
    color: #10b981;
  }

  .action-icon-btn.delete-btn:hover {
    color: #ef4444;
    background: rgba(239, 68, 68, 0.1);
  }

  /* Breathable context quote */
  .card-quote {
    background: transparent;
    border-left: 2px solid rgba(0, 0, 0, 0.12);
    padding: 0.15rem 0 0.15rem 0.5rem;
    font-size: 0.74rem;
    line-height: 1.4;
    color: #64748b;
    font-style: italic;
    margin-bottom: 0.45rem;
  }

  .card-text {
    font-size: 0.81rem;
    line-height: 1.55;
    color: #334155;
    word-break: break-word;
  }

  .card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-top: 0.45rem;
    font-size: 0.68rem;
    color: #94a3b8;
  }

  .resolved-badge {
    color: #10b981;
    font-weight: 600;
    font-size: 0.65rem;
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
  }

  .card-edit-box {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
  }

  .edit-textarea {
    width: 100%;
    box-sizing: border-box;
    font-family: inherit;
    font-size: 0.8rem;
    line-height: 1.4;
    border: 1px solid #0284c7;
    border-radius: 6px;
    padding: 0.45rem;
    resize: vertical;
    outline: none;
    background: #ffffff;
    color: #1e293b;
  }

  .edit-actions {
    display: flex;
    justify-content: flex-end;
    gap: 0.35rem;
  }

  .btn-sm-cancel {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 0.72rem;
    padding: 0.2rem 0.5rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-sm-cancel:hover {
    background: rgba(0, 0, 0, 0.05);
  }

  .btn-sm-save {
    background: #0284c7;
    border: none;
    color: #ffffff;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 0.2rem 0.65rem;
    border-radius: 4px;
    cursor: pointer;
  }

  .btn-sm-save:hover {
    background: #0369a1;
  }

  /* --------------------------------------------------------------------------
     Dark Mode (Refined Slate / Midnight)
     -------------------------------------------------------------------------- */
  :global([data-theme="dark"]) .annotation-card,
  :global(body.dark-theme) .annotation-card {
    background: #1a1b20;
    border-color: rgba(255, 255, 255, 0.08);
    color: #ededed;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.3);
  }

  :global([data-theme="dark"]) .annotation-card:hover,
  :global(body.dark-theme) .annotation-card:hover {
    border-color: rgba(255, 255, 255, 0.18);
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.45);
  }

  :global([data-theme="dark"]) .annotation-card.active,
  :global(body.dark-theme) .annotation-card.active {
    border-color: #38bdf8;
    box-shadow: 0 0 0 1px #38bdf8, 0 6px 20px rgba(56, 189, 248, 0.22);
  }

  :global([data-theme="dark"]) .card-avatar,
  :global(body.dark-theme) .card-avatar {
    background: #23252c;
    color: #94a3b8;
    border-color: rgba(255, 255, 255, 0.08);
  }

  :global([data-theme="dark"]) .card-author,
  :global(body.dark-theme) .card-author {
    color: #f1f5f9;
  }

  :global([data-theme="dark"]) .category-badge,
  :global(body.dark-theme) .category-badge {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .action-icon-btn,
  :global(body.dark-theme) .action-icon-btn {
    color: #64748b;
  }

  :global([data-theme="dark"]) .action-icon-btn:hover,
  :global(body.dark-theme) .action-icon-btn:hover {
    color: #f8fafc;
    background: rgba(255, 255, 255, 0.1);
  }

  :global([data-theme="dark"]) .card-quote,
  :global(body.dark-theme) .card-quote {
    color: #94a3b8;
    border-left-color: rgba(255, 255, 255, 0.15);
  }

  :global([data-theme="dark"]) .card-text,
  :global(body.dark-theme) .card-text {
    color: #cbd5e1;
  }

  :global([data-theme="dark"]) .edit-textarea,
  :global(body.dark-theme) .edit-textarea {
    background: #121316;
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