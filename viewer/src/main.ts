import App from './App.svelte';
import { mount, unmount } from 'svelte';
import * as svelteInternal from 'svelte/internal/client';

let hasInitialized = false;

function initViewer() {
  if (hasInitialized) return;
  hasInitialized = true;

  // Mount document-defined custom Svelte components (if registered)
  mountDocumentComponents();

  // If in print mode or paged media, do not mount interactive overlays
  if (window.matchMedia && window.matchMedia('print').matches) {
    return;
  }

  // Create or relocate root container directly under documentElement (decoupled from body styles and transforms)
  let root = document.getElementById('md-style-viewer-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'md-style-viewer-root';
    document.documentElement.appendChild(root);
  } else if (root.parentElement !== document.documentElement) {
    document.documentElement.appendChild(root);
  }

  const metaTitle = document.querySelector('meta[name="doc-title"]')?.getAttribute('content') || document.title;
  const isPrintOrPaged = document.body.classList.contains('paged-preview') || document.body.classList.contains('print-mode');

  try {
    // Svelte 5 mount
    mount(App, {
      target: root,
      props: {
        title: metaTitle,
        enableHud: !isPrintOrPaged,
        enableInspector: !isPrintOrPaged,
        enableTableFilters: !isPrintOrPaged
      }
    });
  } catch (e) {
    // Svelte 4 legacy fallback
    new (App as any)({
      target: root,
      props: {
        title: metaTitle,
        enableHud: !isPrintOrPaged,
        enableInspector: !isPrintOrPaged,
        enableTableFilters: !isPrintOrPaged
      }
    });
  }
}

/**
 * Discovers and mounts document-defined custom Svelte components.
 * Looks for placeholders: <div class="doc-component-mount" data-component="ComponentName" data-props='{...}'>
 */
function mountDocumentComponents() {
  const customRegistry = (window as any).__MD_STYLE_COMPONENTS__ || {};
  const mounts = document.querySelectorAll<HTMLElement>('.doc-component-mount');

  mounts.forEach(mountEl => {
    if (mountEl.getAttribute('data-mounted') === 'true') return;
    const compName = mountEl.getAttribute('data-component');
    if (!compName) return;

    const Component = customRegistry[compName];
    if (!Component) {
      console.warn(`[md-style] Custom component '${compName}' not found in __MD_STYLE_COMPONENTS__`);
      return;
    }

    let props: Record<string, any> = {};
    const rawProps = mountEl.getAttribute('data-props');
    if (rawProps) {
      try {
        props = JSON.parse(rawProps);
      } catch (err) {
        console.warn(`[md-style] Failed to parse props for component '${compName}':`, err);
      }
    }

    try {
      mountEl.setAttribute('data-mounted', 'true');
      mount(Component, {
        target: mountEl,
        props
      });
    } catch (err) {
      console.error(`[md-style] Error mounting custom component '${compName}':`, err);
    }
  });
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initViewer);
} else {
  initViewer();
}

// Global runtime exports for dynamic document components
export * from 'svelte';
export * as svelteInternal from 'svelte/internal/client';
export {
  initViewer,
  mountDocumentComponents
};
