<script lang="ts">
  import { onMount, onDestroy, tick } from 'svelte';
  import Icon from './Icon.svelte';

  export let isOpen: boolean = false;
  export let svgElement: SVGElement | null = null;
  export let title: string = '';
  export let id: string = '';
  export let i18n: Record<string, string> = {};
  export let onClose: () => void;

  let canvasContainer: HTMLDivElement;
  let scale: number = 1.0;
  let panX: number = 0;
  let panY: number = 0;
  let isDragging: boolean = false;
  let startX: number = 0;
  let startY: number = 0;

  let vbWidth: number = 960;
  let vbHeight: number = 520;
  let initialScale: number = 1.0;

  function getSvgDimensions(): { w: number; h: number } {
    if (!svgElement) return { w: 960, h: 520 };

    // 1. Check viewBox attribute
    const viewBoxAttr = svgElement.getAttribute('viewBox');
    if (viewBoxAttr) {
      const parts = viewBoxAttr.trim().split(/[\s,]+/).map(Number);
      if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
        return { w: parts[2], h: parts[3] };
      }
    }

    // 2. Check explicit width/height attributes
    const wAttr = svgElement.getAttribute('width');
    const hAttr = svgElement.getAttribute('height');
    const parsedW = wAttr ? parseFloat(wAttr) : NaN;
    const parsedH = hAttr ? parseFloat(hAttr) : NaN;
    if (!isNaN(parsedW) && !isNaN(parsedH) && parsedW > 0 && parsedH > 0) {
      return { w: parsedW, h: parsedH };
    }

    // 3. Fallback to bounding rect
    try {
      const rect = svgElement.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        return { w: rect.width, h: rect.height };
      }
    } catch (_) {}

    return { w: 960, h: 520 };
  }

  function fitToScreen() {
    if (!svgElement) return;
    const dims = getSvgDimensions();
    vbWidth = dims.w;
    vbHeight = dims.h;

    if (canvasContainer) {
      const rect = canvasContainer.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        // Leave comfortable breathing room around the diagram
        const availW = Math.max(100, rect.width - 64);
        const availH = Math.max(100, rect.height - 56);
        const fit = Math.min(availW / vbWidth, availH / vbHeight);
        scale = Number(Math.max(0.1, fit).toFixed(2));
        initialScale = scale;
        panX = 0;
        panY = 0;
        return;
      }
    }

    scale = 1.0;
    initialScale = 1.0;
    panX = 0;
    panY = 0;
  }

  $: if (isOpen && svgElement) {
    tick().then(() => {
      fitToScreen();
    });
  }

  function resetView() {
    fitToScreen();
  }

  function zoomIn() {
    scale = Math.min(10.0, Number((scale * 1.25).toFixed(2)));
  }

  function zoomOut() {
    scale = Math.max(0.1, Number((scale / 1.25).toFixed(2)));
  }

  function handleWheel(e: WheelEvent) {
    e.preventDefault();
    const zoomFactor = e.deltaY < 0 ? 1.15 : 0.85;
    const newScale = Math.min(8.0, Math.max(0.2, scale * zoomFactor));
    
    // Zoom toward cursor location
    if (canvasContainer) {
      const rect = canvasContainer.getBoundingClientRect();
      const mouseX = e.clientX - rect.left - rect.width / 2;
      const mouseY = e.clientY - rect.top - rect.height / 2;
      panX -= (mouseX - panX) * (zoomFactor - 1);
      panY -= (mouseY - panY) * (zoomFactor - 1);
    }
    scale = Number(newScale.toFixed(2));
  }

  function handlePointerDown(e: PointerEvent) {
    if (e.button !== 0) return; // Only left click
    isDragging = true;
    startX = e.clientX - panX;
    startY = e.clientY - panY;
    (e.target as HTMLElement)?.setPointerCapture?.(e.pointerId);
  }

  function handlePointerMove(e: PointerEvent) {
    if (!isDragging) return;
    panX = e.clientX - startX;
    panY = e.clientY - startY;
  }

  function handlePointerUp(e: PointerEvent) {
    isDragging = false;
    try {
      (e.target as HTMLElement)?.releasePointerCapture?.(e.pointerId);
    } catch (_) {}
  }

  function handleKeyDown(e: KeyboardEvent) {
    if (!isOpen) return;
    if (e.key === 'Escape') {
      onClose();
    } else if (e.key === '+' || e.key === '=') {
      zoomIn();
    } else if (e.key === '-' || e.key === '_') {
      zoomOut();
    } else if (e.key === '0') {
      resetView();
    }
  }

  function downloadSvg() {
    if (!svgElement) return;
    try {
      const serializer = new XMLSerializer();
      const svgStr = serializer.serializeToString(svgElement);
      const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const rawTitle = title
        .toLowerCase()
        .replace(/[^a-z0-9_-]+/g, '-')
        .replace(/^-|-$/g, '');
      a.download = (rawTitle || id || 'diagram') + '.svg';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.warn('Failed to download SVG:', e);
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeyDown);
  });

  onDestroy(() => {
    window.removeEventListener('keydown', handleKeyDown);
  });
</script>

{#if isOpen && svgElement}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
  <div
    class="lightbox-backdrop"
    role="dialog"
    tabindex="-1"
    aria-modal="true"
    aria-label={title || "Figure zoom"}
    on:click|self={onClose}
  >
    <div class="lightbox-modal">
      <!-- Header bar -->
      <header class="lightbox-header">
        <div class="lightbox-title-group" title={title}>
          <span class="lightbox-dot"></span>
          <span class="lightbox-badge">FIGURE</span>
          <span class="lightbox-title">{title || id || "Figure Viewer"}</span>
        </div>

        <div class="lightbox-controls">
          <div class="zoom-pill">
            <button type="button" class="ctrl-btn" on:click={zoomOut} title="Zoom out (-)" aria-label="Zoom out">
              <Icon name="minus" size={13} />
            </button>
            <span class="zoom-value">{Math.round(scale * 100)}%</span>
            <button type="button" class="ctrl-btn" on:click={zoomIn} title="Zoom in (+)" aria-label="Zoom in">
              <Icon name="plus" size={13} />
            </button>
            <button type="button" class="ctrl-btn reset-btn" on:click={resetView} title="Fit to screen (0)">
              Fit
            </button>
          </div>

          <div class="toolbar-sep"></div>

          <button type="button" class="ctrl-btn action-pill" on:click={downloadSvg} title={i18n.download_svg || "Download SVG"}>
            <Icon name="download" size={13} />
            <span class="btn-text">SVG</span>
          </button>

          <button type="button" class="ctrl-btn close-btn" on:click={onClose} title="Close (Esc)" aria-label="Close">
            <Icon name="x" size={15} />
          </button>
        </div>
      </header>

      <!-- Pan & Zoom canvas -->
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div
        class="lightbox-canvas"
        bind:this={canvasContainer}
        on:wheel={handleWheel}
        on:pointerdown={handlePointerDown}
        on:pointermove={handlePointerMove}
        on:pointerup={handlePointerUp}
        on:pointercancel={handlePointerUp}
        on:dblclick={resetView}
        class:is-dragging={isDragging}
      >
        <div
          class="svg-transform-wrapper"
          style="width: {vbWidth}px; height: {vbHeight}px; transform: translate({panX}px, {panY}px) scale({scale});"
        >
          {@html svgElement.outerHTML}
        </div>
      </div>

      <footer class="lightbox-footer">
        <span class="hint-text">
          Drag to pan • Scroll to zoom • Double-click to reset • <kbd>Esc</kbd> to close
        </span>
      </footer>
    </div>
  </div>
{/if}

<style>
  .lightbox-backdrop {
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    background: rgba(15, 23, 42, 0.82);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    z-index: 99999;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1.5rem;
    box-sizing: border-box;
    animation: fadeIn 0.15s ease-out;
    font-family: var(--font-sans, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif);
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  .lightbox-modal {
    width: 100%;
    max-width: 95vw;
    height: 92vh;
    background: #0f172a;
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 12px;
    box-shadow: 0 25px 60px -15px rgba(0, 0, 0, 0.7);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  :global([data-theme="light"]) .lightbox-modal,
  :global(body.light-theme) .lightbox-modal {
    background: #ffffff;
    border-color: rgba(0, 0, 0, 0.1);
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
  }

  .lightbox-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.65rem 1.25rem;
    background: rgba(15, 23, 42, 0.95);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    flex-shrink: 0;
    gap: 1rem;
    user-select: none;
  }

  :global([data-theme="light"]) .lightbox-header,
  :global(body.light-theme) .lightbox-header {
    background: rgba(248, 250, 252, 0.95);
    border-bottom-color: rgba(0, 0, 0, 0.08);
  }

  .lightbox-title-group {
    display: flex;
    align-items: center;
    gap: 0.65rem;
    overflow: hidden;
    min-width: 0;
  }

  .lightbox-dot {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: #00f0ff;
    box-shadow: 0 0 8px rgba(0, 240, 255, 0.75);
    flex-shrink: 0;
  }

  .lightbox-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    letter-spacing: 0.06em;
    background: rgba(56, 189, 248, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(56, 189, 248, 0.3);
    flex-shrink: 0;
  }

  .lightbox-title {
    font-size: 0.85rem;
    font-weight: 600;
    color: #f1f5f9;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  :global([data-theme="light"]) .lightbox-title,
  :global(body.light-theme) .lightbox-title {
    color: #0f172a;
  }

  .lightbox-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    flex-shrink: 0;
  }

  .zoom-pill {
    display: inline-flex;
    align-items: center;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 6px;
    padding: 0.12rem 0.2rem;
  }

  :global([data-theme="light"]) .zoom-pill,
  :global(body.light-theme) .zoom-pill {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.1);
  }

  .ctrl-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.65rem;
    height: 1.65rem;
    background: transparent;
    border: none;
    border-radius: 4px;
    color: #cbd5e1;
    cursor: pointer;
    transition: background 0.15s, color 0.15s;
    font-family: inherit;
  }

  :global([data-theme="light"]) .ctrl-btn,
  :global(body.light-theme) .ctrl-btn {
    color: #475569;
  }

  .ctrl-btn:hover {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
  }

  :global([data-theme="light"]) .ctrl-btn:hover,
  :global(body.light-theme) .ctrl-btn:hover {
    background: rgba(0, 0, 0, 0.08);
    color: #0f172a;
  }

  .ctrl-btn.reset-btn {
    width: auto;
    padding: 0 0.45rem;
    font-size: 0.72rem;
    font-weight: 600;
  }

  .zoom-value {
    font-size: 0.72rem;
    font-weight: 600;
    font-family: var(--font-mono, ui-monospace, monospace);
    min-width: 2.8rem;
    text-align: center;
    color: #94a3b8;
  }

  .toolbar-sep {
    width: 1px;
    height: 1.25rem;
    background: rgba(255, 255, 255, 0.12);
  }

  :global([data-theme="light"]) .toolbar-sep,
  :global(body.light-theme) .toolbar-sep {
    background: rgba(0, 0, 0, 0.1);
  }

  .action-pill {
    width: auto;
    gap: 0.35rem;
    padding: 0.2rem 0.6rem;
    font-size: 0.72rem;
    font-weight: 600;
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.12);
  }

  :global([data-theme="light"]) .action-pill,
  :global(body.light-theme) .action-pill {
    background: rgba(0, 0, 0, 0.04);
    border-color: rgba(0, 0, 0, 0.1);
  }

  .btn-text {
    font-size: 0.72rem;
  }

  .ctrl-btn.close-btn:hover {
    background: rgba(239, 68, 68, 0.25);
    color: #f87171;
  }

  .lightbox-canvas {
    flex: 1;
    position: relative;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: grab;
    user-select: none;
    background-color: #0b1120;
    background-image: radial-gradient(rgba(255, 255, 255, 0.07) 1px, transparent 1px);
    background-size: 24px 24px;
  }

  :global([data-theme="light"]) .lightbox-canvas,
  :global(body.light-theme) .lightbox-canvas {
    background-color: #f8fafc;
    background-image: radial-gradient(rgba(0, 0, 0, 0.06) 1px, transparent 1px);
  }

  .lightbox-canvas.is-dragging {
    cursor: grabbing;
  }

  .svg-transform-wrapper {
    display: block;
    transform-origin: center center;
    transition: transform 0.05s linear;
    flex-shrink: 0;
  }

  .svg-transform-wrapper :global(svg) {
    display: block !important;
    width: 100% !important;
    height: 100% !important;
    max-width: none !important;
    max-height: none !important;
    margin: 0 !important;
    filter: drop-shadow(0 8px 32px rgba(0, 0, 0, 0.35));
  }

  .lightbox-footer {
    padding: 0.45rem 1.25rem;
    background: rgba(15, 23, 42, 0.95);
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    text-align: center;
    flex-shrink: 0;
    user-select: none;
  }

  :global([data-theme="light"]) .lightbox-footer,
  :global(body.light-theme) .lightbox-footer {
    background: rgba(248, 250, 252, 0.95);
    border-top-color: rgba(0, 0, 0, 0.08);
  }

  .hint-text {
    font-size: 0.72rem;
    color: #64748b;
  }

  kbd {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 3px;
    padding: 0.1rem 0.35rem;
    font-size: 0.68rem;
    font-family: inherit;
    color: #cbd5e1;
  }

  :global([data-theme="light"]) kbd,
  :global(body.light-theme) kbd {
    background: rgba(0, 0, 0, 0.05);
    border-color: rgba(0, 0, 0, 0.15);
    color: #475569;
  }
</style>
