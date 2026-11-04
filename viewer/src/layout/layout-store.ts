import { writable, get } from 'svelte/store';

export type LayoutState = 'zen' | 'reading-with-toc' | 'inspecting' | 'split-overview';
export type TocDisplayMode = 'spine' | 'drawer' | 'hidden';

export interface LayoutStoreState {
  isTocOpen: boolean;
  isInspectorOpen: boolean;
  activeDrawerTab: 'kb' | 'comments';
  tocMode: TocDisplayMode;
  layoutState: LayoutState;
  viewportWidth: number;
  isWideScreen: boolean; // >= 1600px
  canDockSpine: boolean;
  spineRight: number;
  wasTocOpenBeforeInspector: boolean;
}

function checkCanDockSpine(isInspectorActive: boolean): boolean {
  if (typeof window === 'undefined' || typeof document === 'undefined') return false;
  const docEl = document.querySelector('.report-content') || document.querySelector('main') || document.body;
  if (!docEl) return false;
  const baseLeft = (docEl as HTMLElement).offsetLeft || docEl.getBoundingClientRect().left;
  return window.innerWidth >= 1600 || (window.innerWidth >= 1100 && !isInspectorActive && baseLeft >= 160);
}

function computeSpineRight(): number {
  if (typeof window === 'undefined' || typeof document === 'undefined') return 0;
  const docEl = document.querySelector('.report-content') || document.querySelector('main') || document.body;
  if (!docEl) return 0;
  const baseLeft = (docEl as HTMLElement).offsetLeft || docEl.getBoundingClientRect().left;
  return Math.max(16, window.innerWidth - baseLeft + 40);
}

function determineLayoutState(isTocOpen: boolean, isInspectorOpen: boolean): LayoutState {
  if (!isTocOpen && !isInspectorOpen) return 'zen';
  if (isTocOpen && !isInspectorOpen) return 'reading-with-toc';
  if (!isTocOpen && isInspectorOpen) return 'inspecting';
  return 'split-overview';
}

function determineTocMode(isTocOpen: boolean, canDockSpine: boolean): TocDisplayMode {
  if (!isTocOpen) return 'hidden';
  return canDockSpine ? 'spine' : 'drawer';
}

function syncDomAttributes(state: LayoutStoreState) {
  if (typeof document === 'undefined') return;
  const html = document.documentElement;
  const body = document.body;

  html.setAttribute('data-layout-state', state.layoutState);
  html.setAttribute('data-toc-open', String(state.isTocOpen));
  html.setAttribute('data-toc-mode', state.tocMode);
  html.setAttribute('data-inspector-open', String(state.isInspectorOpen));

  // Backward compatibility with legacy styles and tests
  body.classList.toggle('inspector-open', state.isInspectorOpen);
  body.classList.toggle('toc-docked', state.isTocOpen && state.tocMode === 'spine');
}

function isTocDismissedByUser(): boolean {
  if (typeof window === 'undefined') return false;
  try {
    return sessionStorage.getItem('md-style-toc-dismissed') === 'true';
  } catch (_) {
    return false;
  }
}

function setTocDismissedByUser(dismissed: boolean) {
  if (typeof window === 'undefined') return;
  try {
    if (dismissed) {
      sessionStorage.setItem('md-style-toc-dismissed', 'true');
    } else {
      sessionStorage.removeItem('md-style-toc-dismissed');
    }
  } catch (_) {}
}

function createLayoutStore() {
  const initialWidth = typeof window !== 'undefined' ? window.innerWidth : 1440;
  const canDock = checkCanDockSpine(false);
  const shouldOpenDefault = typeof window !== 'undefined'
    ? (initialWidth >= 1100 && !isTocDismissedByUser())
    : false;

  const { subscribe, set, update } = writable<LayoutStoreState>({
    isTocOpen: shouldOpenDefault,
    isInspectorOpen: false,
    activeDrawerTab: 'kb',
    tocMode: shouldOpenDefault ? (canDock ? 'spine' : 'drawer') : 'hidden',
    layoutState: shouldOpenDefault ? 'reading-with-toc' : 'zen',
    viewportWidth: initialWidth,
    isWideScreen: initialWidth >= 1600,
    canDockSpine: canDock,
    spineRight: computeSpineRight(),
    wasTocOpenBeforeInspector: false
  });

  function updateLayout(updater: (curr: LayoutStoreState) => Partial<LayoutStoreState>) {
    update((curr) => {
      const partial = updater(curr);
      const next = { ...curr, ...partial };

      const canDockSpine = checkCanDockSpine(next.isInspectorOpen);
      const spineRight = computeSpineRight();
      const layoutState = determineLayoutState(next.isTocOpen, next.isInspectorOpen);
      const tocMode = determineTocMode(next.isTocOpen, canDockSpine);
      const isWideScreen = next.viewportWidth >= 1600;

      const finalState: LayoutStoreState = {
        ...next,
        canDockSpine,
        spineRight,
        layoutState,
        tocMode,
        isWideScreen
      };

      syncDomAttributes(finalState);
      return finalState;
    });
  }

  function handleResize() {
    if (typeof window === 'undefined') return;
    const w = window.innerWidth;
    updateLayout((curr) => ({ viewportWidth: w }));
  }

  function init() {
    if (typeof window === 'undefined') return;
    window.addEventListener('resize', handleResize, { passive: true });

    // Ensure ToC is open on desktop by default if user hasn't explicitly dismissed it
    const canDock = checkCanDockSpine(false);
    const dismissed = isTocDismissedByUser();
    if (canDock && !dismissed) {
      updateLayout(() => ({ isTocOpen: true }));
    } else {
      syncDomAttributes(get({ subscribe }));
    }
  }

  function destroy() {
    if (typeof window === 'undefined') return;
    window.removeEventListener('resize', handleResize);
  }

  function toggleToc() {
    updateLayout((curr) => {
      const willOpen = !curr.isTocOpen;
      setTocDismissedByUser(!willOpen);
      return {
        isTocOpen: willOpen,
        wasTocOpenBeforeInspector: willOpen ? false : curr.wasTocOpenBeforeInspector
      };
    });
  }

  function openToc() {
    setTocDismissedByUser(false);
    updateLayout((curr) => ({
      isTocOpen: true,
      wasTocOpenBeforeInspector: false
    }));
  }

  function closeToc() {
    setTocDismissedByUser(true);
    updateLayout((curr) => ({
      isTocOpen: false,
      wasTocOpenBeforeInspector: false
    }));
  }

  function toggleInspector(tab?: 'kb' | 'comments') {
    updateLayout((curr) => {
      const willClose = curr.isInspectorOpen && (!tab || curr.activeDrawerTab === tab);
      if (willClose) {
        // Closing inspector: restore ToC if previously stowed
        const restoreToc = curr.wasTocOpenBeforeInspector;
        return {
          isInspectorOpen: false,
          isTocOpen: restoreToc ? true : curr.isTocOpen,
          wasTocOpenBeforeInspector: false
        };
      } else {
        // Opening inspector: on screens < 1600px auto-stow ToC
        const targetTab = tab || curr.activeDrawerTab;
        const autoStow = !curr.isWideScreen && curr.isTocOpen;
        return {
          isInspectorOpen: true,
          activeDrawerTab: targetTab,
          isTocOpen: autoStow ? false : curr.isTocOpen,
          wasTocOpenBeforeInspector: autoStow ? true : curr.wasTocOpenBeforeInspector
        };
      }
    });
  }

  function openInspector(tab: 'kb' | 'comments' = 'kb') {
    updateLayout((curr) => {
      const autoStow = !curr.isWideScreen && curr.isTocOpen;
      return {
        isInspectorOpen: true,
        activeDrawerTab: tab,
        isTocOpen: autoStow ? false : curr.isTocOpen,
        wasTocOpenBeforeInspector: autoStow ? true : curr.wasTocOpenBeforeInspector
      };
    });
  }

  function closeInspector() {
    updateLayout((curr) => {
      const restoreToc = curr.wasTocOpenBeforeInspector;
      return {
        isInspectorOpen: false,
        isTocOpen: restoreToc ? true : curr.isTocOpen,
        wasTocOpenBeforeInspector: false
      };
    });
  }

  function setDrawerTab(tab: 'kb' | 'comments') {
    updateLayout(() => ({ activeDrawerTab: tab }));
  }

  return {
    subscribe,
    init,
    destroy,
    toggleToc,
    openToc,
    closeToc,
    toggleInspector,
    openInspector,
    closeInspector,
    setDrawerTab,
    refreshDocking: () => updateLayout((curr) => ({}))
  };
}

export const layoutStore = createLayoutStore();
