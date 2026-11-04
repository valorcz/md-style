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
    desiredTop: number;
    top: number;
  }

  let positionedCards: PositionedCard[] = [];
  let gutterLeft: number = 0;
  let isPositioned: boolean = false;
  let isNarrowMode: boolean = false;

  async function calculatePositions() {
    await tick();
    const unresolved = annotations.filter(a => !a.resolved);
    const root = document.querySelector('.report-content') || document.querySelector('main') || document.body;
    if (!root) return;

    const docRect = root.getBoundingClientRect();
    const isTocDocked = typeof document !== 'undefined' && document.body.classList.contains('toc-docked');

    const spaceRight = window.innerWidth - docRect.right;
    const spaceLeft = docRect.left;

    // 1. Dynamic horizontal docking: Always dock to the RIGHT of the document
    // (while ToC sits as a quiet spine on the LEFT). Never encroach into document text!
    const CARD_WIDTH = 280;
    const GUTTER_GAP = 24;

    gutterLeft = docRect.right + window.scrollX + GUTTER_GAP;
    isPositioned = true;

    // 2. Initial vertical positioning pass
    const items: { annotation: DocumentAnnotation; desiredTop: number }[] = [];
    for (const ann of unresolved) {
      const range = deserializeRange(ann.range, root as HTMLElement);
      let top = 0;
      if (range) {
        const rect = range.getBoundingClientRect();
        top = window.scrollY + rect.top;
      } else {
        const blocks = root.querySelectorAll('p, li, h1, h2, h3, blockquote, tr');
        const blk = blocks[ann.range.blockIndex];
        if (blk) {
          const rect = blk.getBoundingClientRect();
          top = window.scrollY + rect.top;
        }
      }
      items.push({ annotation: ann, desiredTop: Math.max(54, top) });
    }

    // Sort strictly by vertical anchor position
    items.sort((a, b) => a.desiredTop - b.desiredTop);

    // Initial coarse layout
    let currentY = 0;
    const initialCards: PositionedCard[] = [];
    for (const item of items) {
      const estH = estimateCardHeight(item.annotation);
      const topPos = Math.max(item.desiredTop, currentY);
      initialCards.push({
        annotation: item.annotation,
        desiredTop: item.desiredTop,
        top: topPos
      });
      currentY = topPos + estH + 12;
    }
    positionedCards = initialCards;

    // 3. Second pass: Measure REAL rendered DOM heights to guarantee 0 vertical overlap
    await tick();
    const gutterEl = document.querySelector('.margin-gutter');
    if (gutterEl) {
      const cardEls = Array.from(gutterEl.querySelectorAll<HTMLElement>('.gutter-item'));
      if (cardEls.length === positionedCards.length) {
        let realY = 0;
        let changed = false;
        const refinedCards = positionedCards.map((c, i) => {
          const desired = c.desiredTop;
          const actualHeight = cardEls[i]?.offsetHeight || 100;
          const finalTop = Math.max(desired, realY);
          realY = finalTop + actualHeight + 12; // 12px guaranteed collision-free gap
          if (Math.abs(finalTop - c.top) > 1) {
            changed = true;
          }
          return { annotation: c.annotation, desiredTop: c.desiredTop, top: finalTop };
        });
        if (changed) {
          positionedCards = refinedCards;
        }
      }
    }
  }

  function estimateCardHeight(ann: DocumentAnnotation): number {
    const text = ann.text || '';
    const lineCount = text.split('\n').length;
    const hasCodeBlock = text.includes('```');
    const baseHeight = 110;
    const codeExtra = hasCodeBlock ? 80 : 0;
    const lineExtra = Math.min(180, lineCount * 20);
    const lengthExtra = Math.min(120, Math.floor(text.length / 45) * 18);
    return Math.min(400, baseHeight + codeExtra + lineExtra + lengthExtra);
  }

  $: if (annotations) {
    calculatePositions();
  }

  $: if (activeAnnotationId) {
    calculatePositions();
  }

  onMount(() => {
    calculatePositions();
    window.addEventListener('resize', calculatePositions);

    // Watch for toc-docked or inspector-open class changes on body
    const observer = new MutationObserver((mutations) => {
      for (const m of mutations) {
        if (m.attributeName === 'class') {
          setTimeout(calculatePositions, 50);
          break;
        }
      }
    });
    observer.observe(document.body, { attributes: true });

    return () => {
      window.removeEventListener('resize', calculatePositions);
      observer.disconnect();
    };
  });
</script>

<aside
  class="margin-gutter"
  aria-label="Review margin comments"
  style="left: {gutterLeft}px; opacity: {isPositioned ? 1 : 0};"
>
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
    top: 0;
    width: 280px;
    pointer-events: none;
    z-index: 1000;
    transition: left 0.22s cubic-bezier(0.16, 1, 0.3, 1), opacity 0.15s ease;
  }

  .gutter-item {
    position: absolute;
    left: 0;
    right: 0;
    pointer-events: auto;
    transition: top 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  @media (max-width: 1100px) {
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
