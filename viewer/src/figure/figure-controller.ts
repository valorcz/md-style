/**
 * viewer/src/figure/figure-controller.ts
 * Headless Controller for Figure Interactivity.
 * Encapsulates wide breakout toggling, SVG copying, and file downloading.
 */

export interface FigureActionCallbacks {
  onToggleWide?: (isWide: boolean) => void;
  onCopySvg?: (success: boolean) => void;
  onOpenLightbox?: (detail: { svgElement: SVGElement; title: string; id: string }) => void;
}

export class FigureController {
  private figureEl: HTMLElement;
  private isWideState: boolean = false;
  private isFullscreenState: boolean = false;

  constructor(figureEl: HTMLElement) {
    this.figureEl = figureEl;
    this.isWideState = figureEl.classList.contains('wide') || figureEl.classList.contains('breakout');
    this.isFullscreenState = figureEl.classList.contains('component-fullscreen');
  }

  get isWide(): boolean {
    return this.isWideState;
  }

  get isFullscreen(): boolean {
    return this.isFullscreenState;
  }

  get isComponent(): boolean {
    return this.figureEl.classList.contains('doc-component-container') ||
           this.figureEl.hasAttribute('data-component') ||
           this.figureEl.querySelector('.doc-component-mount') !== null;
  }

  getCaptionText(): string {
    const captionEl = this.figureEl.querySelector('figcaption');
    return captionEl?.textContent?.trim() || this.figureEl.getAttribute('id') || 'Figure';
  }

  getSvgElement(): SVGElement | null {
    return this.figureEl.querySelector('svg');
  }

  toggleWide(): boolean {
    this.isWideState = !this.isWideState;
    this.figureEl.classList.toggle('wide', this.isWideState);
    return this.isWideState;
  }

  toggleFullscreen(): boolean {
    this.isFullscreenState = !this.isFullscreenState;
    this.figureEl.classList.toggle('component-fullscreen', this.isFullscreenState);
    if (typeof document !== 'undefined') {
      document.body.classList.toggle('has-component-fullscreen', this.isFullscreenState);
    }
    return this.isFullscreenState;
  }

  async copySvg(): Promise<boolean> {
    const svgEl = this.getSvgElement();
    if (!svgEl) return false;
    try {
      const serializer = new XMLSerializer();
      const svgStr = serializer.serializeToString(svgEl);
      await navigator.clipboard.writeText(svgStr);
      return true;
    } catch (e) {
      console.warn('Failed to copy SVG to clipboard:', e);
      return false;
    }
  }

  downloadSvg(filename?: string): boolean {
    const svgEl = this.getSvgElement();
    if (!svgEl) return false;
    try {
      const serializer = new XMLSerializer();
      const svgStr = serializer.serializeToString(svgEl);
      const blob = new Blob([svgStr], { type: 'image/svg+xml;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      const baseName = filename || this.getCaptionText().toLowerCase().replace(/[^a-z0-9_-]+/g, '-');
      a.download = `${baseName || 'diagram'}.svg`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      return true;
    } catch (e) {
      console.warn('Failed to download SVG:', e);
      return false;
    }
  }
}
