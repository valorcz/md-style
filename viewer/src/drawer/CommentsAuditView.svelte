<script lang="ts">
  import { annotationStore } from '../annotations/store';
  import AnnotationCard from '../annotations/AnnotationCard.svelte';
  import { exportUpdatedHtmlBundle, exportCriticMarkdown } from '../annotations/export-bundle';
  import Icon from '../components/Icon.svelte';

  export let annotations: any[] = [];
  export let activeAnnotationId: string | null = null;

  function handleExportHtml() {
    exportUpdatedHtmlBundle(annotations, document.title);
  }

  function handleExportMarkdown() {
    const mdScript = document.getElementById('md-style-source-markdown');
    const rawMd = mdScript ? mdScript.textContent?.replace(/<\\\/script>/g, '<' + '/script>').trim() || '' : '';
    exportCriticMarkdown(rawMd, annotations, document.title);
  }
</script>

<div class="comments-management-view">
  <div class="export-actions-row">
    <button
      class="export-btn export-html-btn"
      on:click={handleExportHtml}
      title="Download standalone HTML report with comments embedded"
    >
      <Icon name="box" size={13} />
      <span>Export HTML Bundle</span>
    </button>
    <button
      class="export-btn export-md-btn"
      on:click={handleExportMarkdown}
      title="Download source Markdown with CriticMarkup notes"
    >
      <Icon name="file-text" size={13} />
      <span>Export CriticMarkup .md</span>
    </button>
  </div>

  {#if annotations.length > 0}
    <div class="comments-list">
      {#each annotations as ann (ann.id)}
        <AnnotationCard
          annotation={ann}
          isActive={activeAnnotationId === ann.id}
          on:select={(e) => annotationStore.setActive(e.detail)}
          on:update={(e) => annotationStore.updateAnnotation(e.detail.id, e.detail.text, e.detail.category)}
          on:delete={(e) => annotationStore.deleteAnnotation(e.detail)}
          on:toggleResolved={(e) => annotationStore.toggleResolved(e.detail)}
        />
      {/each}
    </div>
  {:else}
    <div class="empty-comments-notice">
      <span class="empty-icon"><Icon name="message-square" size={24} /></span>
      <p><strong>No comments yet</strong></p>
      <p class="empty-subtitle">Select any text in the document to attach comments, insights, corrections, or praise.</p>
    </div>
  {/if}
</div>

<style>
  .comments-management-view {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    height: 100%;
  }
  .export-actions-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.5rem;
  }
  .export-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    padding: 0.45rem 0.6rem;
    font-size: 0.74rem;
    font-weight: 600;
    border-radius: 4px;
    border: none;
    cursor: pointer;
    transition: background 0.15s ease;
    white-space: nowrap;
    text-align: center;
    font-family: inherit;
  }
  .export-html-btn {
    background: #0284c7;
    color: #fff;
  }
  .export-html-btn:hover { background: #0369a1; }
  .export-md-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #cbd5e1;
  }
  .export-md-btn:hover { background: rgba(255, 255, 255, 0.18); color: #fff; }
  .comments-list {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
    overflow-y: auto;
  }
  .empty-comments-notice {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 3rem 1.5rem;
    text-align: center;
    color: #94a3b8;
  }
  .empty-icon { font-size: 2rem; margin-bottom: 0.5rem; }
  .empty-subtitle { font-size: 0.78rem; color: #64748b; margin-top: 0.25rem; }

  /* Light Theme */
  :global([data-theme="light"]) .export-md-btn,
  :global(body.light-theme) .export-md-btn,
  :global(body.theme-forensic-dossier) .export-md-btn {
    background: #f1f5f9;
    border: 1px solid #cbd5e1;
    color: #334155;
  }
  :global([data-theme="light"]) .export-md-btn:hover,
  :global(body.light-theme) .export-md-btn:hover,
  :global(body.theme-forensic-dossier) .export-md-btn:hover {
    background: #e2e8f0;
    color: #0f172a;
  }
</style>
