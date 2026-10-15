<script lang="ts">
  import { onMount, tick } from 'svelte';
  import type { DocumentAnnotation } from './types';
  import AnnotationCard from './AnnotationCard.svelte';
  import { annotationStore } from './store';
  import { deserializeRange } from './dom-anchor';

  export let annotations: DocumentAnnotation[] = [];
  export let activeAnnotationId: string | null = null;

  interface PositionedCard {
    annotation: DocumentAnnotation;
    top: number;
  }

  let positionedCards: PositionedCard[] = [];

  async function calculatePositions() {
    await tick();
    const unresolved = annotations.filter(a => !a.resolved);
    const root = document.querySelector('.report-content') || document.body;
    const items: { annotation: DocumentAnnotation; desiredTop: number }[] = [];

    for (const ann of unresolved) {
      const range = deserializeRange(ann.range, root as HTMLElement);
      let top = 0;
      if (range) {
        const rect = range.getBoundingClientRect();
        top = window.scrollY + rect.top - 40; // account for HUD
      } else {
        // Fallback: estimate from blockIndex
        const blocks = root.querySelectorAll('p, li, h1, h2, h3, blockquote, tr');
        const blk = blocks[ann.range.blockIndex];
        if (blk) {
          const rect = blk.getBoundingClientRect();
          top = window.scrollY + rect.top - 40;
        }
      }
      items.push({ annotation: ann, desiredTop: Math.max(0, top) });
    }

    // Sort by desired vertical position
    items.sort((a, b) => a.desiredTop - b.desiredTop);

    // Collision-avoidance stacking pass using dynamic content height estimation
    const result: PositionedCard[] = [];
    let currentY = 0;

    for (const item of items) {
      const estimatedHeight = estimateCardHeight(item.annotation);
      let finalTop = Math.max(item.desiredTop, currentY);
      result.push({
        annotation: item.annotation,
        top: finalTop
      });
      currentY = finalTop + estimatedHeight + 8;
    }

    positionedCards = result;
  }

  function estimateCardHeight(ann: DocumentAnnotation): number {
    const text = ann.text || '';
    const lineCount = text.split('\n').length;
    const hasCodeBlock = text.includes('```');
    const baseHeight = 90;
    const codeExtra = hasCodeBlock ? 80 : 0;
    const lineExtra = Math.min(160, lineCount * 18);
    const lengthExtra = Math.min(100, Math.floor(text.length / 50) * 16);
    return Math.min(350, baseHeight + codeExtra + lineExtra + lengthExtra);
  }

  $: if (annotations) {
    calculatePositions();
  }

  onMount(() => {
    calculatePositions();
    window.addEventListener('resize', calculatePositions);
    return () => {
      window.removeEventListener('resize', calculatePositions);
    };
  });
</script>

<aside class="margin-gutter" aria-label="Review margin comments">
  {#each positionedCards as item (item.annotation.id)}
    <div class="gutter-item" style="top: {item.top}px;">
      <AnnotationCard
        annotation={item.annotation}
        isActive={activeAnnotationId === item.annotation.id}
        on:select={(e) => annotationStore.setActive(e.detail)}
        on:update={(e) => annotationStore.updateAnnotation(e.detail.id, e.detail.text, e.detail.category)}
        on:delete={(e) => annotationStore.deleteAnnotation(e.detail)}
        on:toggleResolved={(e) => annotationStore.toggleResolved(e.detail)}
      />
    </div>
  {/each}
</aside>

<style>
  .margin-gutter {
    position: absolute;
    top: 40px;
    right: 2rem;
    width: 280px;
    pointer-events: none;
    z-index: 1000;
  }

  .gutter-item {
    position: absolute;
    left: 0;
    right: 0;
    pointer-events: auto;
    transition: top 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @media (max-width: 1280px) {
    .margin-gutter {
      display: none !important;
    }
  }

  @media print {
    .margin-gutter {
      display: none !important;
    }
  }
</style>
