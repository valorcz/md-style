import App from './App.svelte';
import { mount } from 'svelte';

let hasInitialized = false;

function initViewer() {
  if (hasInitialized) return;
  hasInitialized = true;

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

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initViewer);
} else {
  initViewer();
}

export { initViewer };
