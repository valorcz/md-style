/**
 * viewer/src/figure/figure-geometry.ts
 * Unified Client-Side SVG Geometry Extraction and Dimension Calculation.
 * Shared by FigureLightbox, FigureToolbar, and client-side fallback diagram renderers.
 */

export interface FigureDimensions {
  w: number;
  h: number;
  aspectRatio: number;
  orientation: 'portrait' | 'landscape' | 'square' | 'ultrawide';
}

/**
 * Extracts width and height in px from an SVG element using viewBox, attributes, or bounding box.
 */
export function getSvgDimensions(svgElement: SVGElement | null): FigureDimensions {
  if (!svgElement) {
    return { w: 960, h: 520, aspectRatio: 960 / 520, orientation: 'landscape' };
  }

  // 1. Check parent figure dataset attributes if already calculated at build-time
  const parentFig = svgElement.closest('figure');
  if (parentFig) {
    const natW = parseFloat(parentFig.getAttribute('data-natural-w') || '');
    const natH = parseFloat(parentFig.getAttribute('data-natural-h') || '');
    if (!isNaN(natW) && !isNaN(natH) && natW > 0 && natH > 0) {
      const ar = natW / natH;
      const orient = (parentFig.getAttribute('data-orientation') as any) || classifyOrientation(ar);
      return { w: natW, h: natH, aspectRatio: ar, orientation: orient };
    }
  }

  // 2. Check viewBox attribute
  const viewBoxAttr = svgElement.getAttribute('viewBox');
  if (viewBoxAttr) {
    const parts = viewBoxAttr.trim().split(/[\s,]+/).map(Number);
    if (parts.length === 4 && parts[2] > 0 && parts[3] > 0) {
      const w = parts[2];
      const h = parts[3];
      const ar = w / h;
      return { w, h, aspectRatio: ar, orientation: classifyOrientation(ar) };
    }
  }

  // 3. Check width and height attributes
  const wAttr = svgElement.getAttribute('width');
  const hAttr = svgElement.getAttribute('height');
  const parsedW = wAttr ? parseFloat(wAttr) : NaN;
  const parsedH = hAttr ? parseFloat(hAttr) : NaN;
  if (!isNaN(parsedW) && !isNaN(parsedH) && parsedW > 0 && parsedH > 0) {
    const ar = parsedW / parsedH;
    return { w: parsedW, h: parsedH, aspectRatio: ar, orientation: classifyOrientation(ar) };
  }

  // 4. Fallback to getBoundingClientRect or getBBox
  try {
    const bbox = (svgElement as any).getBBox?.();
    if (bbox && bbox.width > 0 && bbox.height > 0) {
      const ar = bbox.width / bbox.height;
      return { w: bbox.width, h: bbox.height, aspectRatio: ar, orientation: classifyOrientation(ar) };
    }
    const rect = svgElement.getBoundingClientRect();
    if (rect.width > 0 && rect.height > 0) {
      const ar = rect.width / rect.height;
      return { w: rect.width, h: rect.height, aspectRatio: ar, orientation: classifyOrientation(ar) };
    }
  } catch (_) {}

  return { w: 960, h: 520, aspectRatio: 960 / 520, orientation: 'landscape' };
}

export function classifyOrientation(aspectRatio: number): 'portrait' | 'landscape' | 'square' | 'ultrawide' {
  if (aspectRatio < 0.75) return 'portrait';
  if (aspectRatio > 1.8) return 'ultrawide';
  if (aspectRatio >= 0.95 && aspectRatio <= 1.05) return 'square';
  return 'landscape';
}

/**
 * Calculates optimal scale and translation to fit an SVG inside a viewport bounding box.
 */
export function calculateFitToScreen(
  svgDims: FigureDimensions,
  containerRect: { width: number; height: number },
  padding: { x: number; y: number } = { x: 64, y: 56 }
): { scale: number; panX: number; panY: number } {
  if (containerRect.width <= 0 || containerRect.height <= 0) {
    return { scale: 1.0, panX: 0, panY: 0 };
  }

  const availW = Math.max(100, containerRect.width - padding.x);
  const availH = Math.max(100, containerRect.height - padding.y);
  const fit = Math.min(availW / svgDims.w, availH / svgDims.h);
  const scale = Number(Math.max(0.1, fit).toFixed(2));

  return { scale, panX: 0, panY: 0 };
}
