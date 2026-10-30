<script lang="ts">
  import Icon from './Icon.svelte';
  import { FigureController } from '../figure/figure-controller';

  export let figureElement: HTMLElement;
  export let i18n: Record<string, string> = {};
  export let onOpenLightbox: ((detail: { svgElement: SVGElement; title: string; id: string }) => void) | undefined = undefined;

  let controller: FigureController;
  let isWide: boolean = false;
  let copied: boolean = false;

  $: if (figureElement) {
    controller = new FigureController(figureElement);
    isWide = controller.isWide;
  }

  function toggleWide() {
    if (!controller) return;
    isWide = controller.toggleWide();
  }

  function handleOpenLightbox() {
    if (!figureElement || !onOpenLightbox || !controller) return;
    const svgEl = controller.getSvgElement();
    if (!svgEl) return;
    onOpenLightbox({
      svgElement: svgEl,
      title: controller.getCaptionText(),
      id: figureElement.getAttribute('id') || 'figure'
    });
  }

  async function copySvg() {
    if (!controller) return;
    const success = await controller.copySvg();
    if (success) {
      copied = true;
      setTimeout(() => { copied = false; }, 2000);
    }
  }

  function downloadSvg() {
    if (!controller) return;
    controller.downloadSvg();
  }
</script>

<div class="figure-toolbar" role="toolbar" aria-label="Figure tools">
  <button
    type="button"
    class="fig-btn"
    title={i18n.zoom || "Zoom & Pan Lightbox"}
    on:click|stopPropagation={handleOpenLightbox}
  >
    <Icon name="maximize" size={13} />
    <span class="btn-label">{i18n.zoom || "Zoom"}</span>
  </button>

  <button
    type="button"
    class="fig-btn"
    class:active={isWide}
    title={isWide ? (i18n.collapse_width || "Standard width") : (i18n.expand_width || "Expand width")}
    on:click|stopPropagation={toggleWide}
  >
    <Icon name="expand" size={13} />
    <span class="btn-label">{isWide ? (i18n.standard || "Normal") : (i18n.wide || "Wide")}</span>
  </button>

  <button
    type="button"
    class="fig-btn"
    title={copied ? (i18n.copied || "Copied!") : (i18n.copy_svg || "Copy SVG")}
    on:click|stopPropagation={copySvg}
  >
    <Icon name={copied ? "check" : "copy"} size={13} />
    <span class="btn-label">{copied ? (i18n.copied || "Copied") : (i18n.copy || "Copy")}</span>
  </button>

  <button
    type="button"
    class="fig-btn"
    title={i18n.download_svg || "Download SVG"}
    on:click|stopPropagation={downloadSvg}
  >
    <Icon name="download" size={13} />
  </button>
</div>

<style>
  .figure-toolbar {
    position: absolute;
    top: 0.75rem;
    right: 0.75rem;
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.4rem;
    background: rgba(255, 255, 255, 0.92);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(226, 232, 240, 0.9);
    border-radius: 9999px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.1);
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.18s ease, transform 0.18s ease;
    transform: translateY(-2px);
    z-index: 20;
  }

  /* Force icon SVGs inside toolbar to stay small */
  .figure-toolbar :global(svg),
  .fig-btn :global(svg) {
    width: 14px !important;
    height: 14px !important;
    min-width: 14px !important;
    max-width: 14px !important;
    min-height: 14px !important;
    max-height: 14px !important;
    flex-shrink: 0 !important;
    display: inline-block !important;
    margin: 0 !important;
  }

  /* Reveal on hover of parent figure or when focused inside */
  :global(figure:hover) .figure-toolbar,
  :global(figure:focus-within) .figure-toolbar,
  .figure-toolbar:hover,
  .figure-toolbar:focus-within {
    opacity: 1;
    pointer-events: auto;
    transform: translateY(0);
  }

  .fig-btn {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.25rem 0.55rem;
    font-size: 0.72rem;
    font-weight: 500;
    color: var(--color-text-secondary, #475569);
    background: transparent;
    border: none;
    border-radius: 9999px;
    cursor: pointer;
    line-height: 1;
    white-space: nowrap;
    transition: background-color 0.15s ease, color 0.15s ease;
  }

  .fig-btn:hover {
    background: var(--color-surface-hover, rgba(0, 0, 0, 0.06));
    color: var(--color-text-primary, #0f172a);
  }

  .fig-btn.active {
    background: var(--color-primary-subtle, #eff6ff);
    color: var(--color-primary, #2563eb);
    font-weight: 600;
  }

  .btn-label {
    display: inline-block;
  }

  @media (max-width: 640px) {
    .btn-label {
      display: none;
    }
  }

  /* Dark mode theme */
  :global([data-theme="dark"]) .figure-toolbar,
  :global(body.dark-theme) .figure-toolbar {
    background: rgba(30, 41, 59, 0.88);
    border-color: rgba(255, 255, 255, 0.12);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
  }

  :global([data-theme="dark"]) .fig-btn,
  :global(body.dark-theme) .fig-btn {
    color: #cbd5e1;
  }

  :global([data-theme="dark"]) .fig-btn:hover,
  :global(body.dark-theme) .fig-btn:hover {
    background: rgba(255, 255, 255, 0.1);
    color: #f8fafc;
  }

  :global([data-theme="dark"]) .fig-btn.active,
  :global(body.dark-theme) .fig-btn.active {
    background: rgba(56, 189, 248, 0.2);
    color: #38bdf8;
  }

  /* Don't show toolbar in print */
  @media print {
    .figure-toolbar {
      display: none !important;
    }
  }
</style>
