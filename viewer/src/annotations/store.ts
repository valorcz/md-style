import { writable, get } from 'svelte/store';
import type { DocumentAnnotation, AnnotationsManifest, AnnotationCategory, RangeSelector } from './types';
import { DocumentHighlighter } from './dom-anchor';

export interface AnnotationStoreState {
  annotations: DocumentAnnotation[];
  activeAnnotationId: string | null;
  educativeMode: boolean;
  documentKey: string;
}

function createAnnotationStore() {
  const { subscribe, set, update } = writable<AnnotationStoreState>({
    annotations: [],
    activeAnnotationId: null,
    educativeMode: true,
    documentKey: 'default'
  });

  const highlighter = new DocumentHighlighter();

  function getDocumentKey(): string {
    const metaFingerprint = document.querySelector('meta[name="doc-fingerprint"]')?.getAttribute('content');
    const docTitle = document.querySelector('meta[name="doc-title"]')?.getAttribute('content') || document.title;
    return metaFingerprint || (docTitle ? `doc-${docTitle.toLowerCase().replace(/[^a-z0-9_-]+/g, '-')}` : 'md-style-doc');
  }

  function init() {
    const docKey = getDocumentKey();
    const storageKey = `md-style:annotations:${docKey}`;

    // 1. Load baseline from embedded <script id="md-style-annotations">
    let embedded: DocumentAnnotation[] = [];
    const scriptEl = document.getElementById('md-style-annotations');
    if (scriptEl && scriptEl.textContent) {
      try {
        const parsed: AnnotationsManifest = JSON.parse(scriptEl.textContent);
        if (parsed && Array.isArray(parsed.annotations)) {
          embedded = parsed.annotations;
        }
      } catch (e) {
        console.warn('[Annotations] Failed to parse embedded #md-style-annotations:', e);
      }
    }

    // 2. Merge with localStorage session additions and tombstones
    let localSaved: DocumentAnnotation[] = [];
    let tombstones: string[] = [];
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          localSaved = parsed;
        } else if (parsed && Array.isArray(parsed.annotations)) {
          localSaved = parsed.annotations;
          tombstones = Array.isArray(parsed.tombstones) ? parsed.tombstones : [];
        }
      }
    } catch (e) {
      console.warn('[Annotations] Failed to read localStorage:', e);
    }

    // Union by ID (localStorage overrides or appends, ignoring tombstones)
    const map = new Map<string, DocumentAnnotation>();
    const tombstoneSet = new Set(tombstones);

    for (const ann of embedded) {
      if (!tombstoneSet.has(ann.id)) {
        map.set(ann.id, ann);
      }
    }
    for (const ann of localSaved) {
      if (!tombstoneSet.has(ann.id)) {
        map.set(ann.id, ann);
      }
    }

    const merged = Array.from(map.values());

    update(s => ({
      ...s,
      documentKey: docKey,
      annotations: merged
    }));

    requestAnimationFrame(() => {
      highlighter.applyHighlights(merged);
    });
  }

  function persist(items: DocumentAnnotation[], tombstones?: string[]) {
    const state = get({ subscribe });
    const storageKey = `md-style:annotations:${state.documentKey}`;
    try {
      // Retain existing tombstones if not provided
      let currentTombstones = tombstones || [];
      if (!tombstones) {
        const existing = localStorage.getItem(storageKey);
        if (existing) {
          try {
            const parsed = JSON.parse(existing);
            if (parsed && Array.isArray(parsed.tombstones)) {
              currentTombstones = parsed.tombstones;
            }
          } catch (parseErr) {
            console.warn('[Annotations] Failed to parse existing tombstones from localStorage, resetting:', parseErr);
            currentTombstones = [];
          }
        }
      }
      localStorage.setItem(storageKey, JSON.stringify({
        annotations: items,
        tombstones: currentTombstones
      }));
    } catch (e) {
      console.warn('[Annotations] Failed to persist to localStorage:', e);
    }

    if (state.educativeMode) {
      highlighter.applyHighlights(items);
    }
  }

  function addAnnotation(param: {
    category: AnnotationCategory;
    text: string;
    author?: string;
    range: RangeSelector;
    tags?: string[];
  }): DocumentAnnotation {
    const id = `ann-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`;
    const newAnn: DocumentAnnotation = {
      id,
      createdAt: new Date().toISOString(),
      author: param.author || 'Reviewer',
      category: param.category,
      text: param.text,
      range: param.range,
      resolved: false,
      tags: param.tags || []
    };

    update(s => {
      const next = [newAnn, ...s.annotations];
      persist(next);
      return { ...s, annotations: next, activeAnnotationId: id };
    });

    return newAnn;
  }

  function updateAnnotation(id: string, text: string, category?: AnnotationCategory) {
    update(s => {
      const next = s.annotations.map(a => {
        if (a.id === id) {
          return {
            ...a,
            text,
            category: category || a.category,
            updatedAt: new Date().toISOString()
          };
        }
        return a;
      });
      persist(next);
      return { ...s, annotations: next };
    });
  }

  function deleteAnnotation(id: string) {
    update(s => {
      const next = s.annotations.filter(a => a.id !== id);
      const storageKey = `md-style:annotations:${s.documentKey}`;
      let currentTombstones: string[] = [];
      try {
        const existing = localStorage.getItem(storageKey);
        if (existing) {
          const parsed = JSON.parse(existing);
          if (parsed && Array.isArray(parsed.tombstones)) {
            currentTombstones = parsed.tombstones;
          }
        }
      } catch (e) {}

      if (!currentTombstones.includes(id)) {
        currentTombstones.push(id);
      }

      persist(next, currentTombstones);
      return {
        ...s,
        annotations: next,
        activeAnnotationId: s.activeAnnotationId === id ? null : s.activeAnnotationId
      };
    });
  }

  function toggleResolved(id: string) {
    update(s => {
      const next = s.annotations.map(a => (a.id === id ? { ...a, resolved: !a.resolved } : a));
      persist(next);
      return { ...s, annotations: next };
    });
  }

  function setActive(id: string | null) {
    update(s => ({ ...s, activeAnnotationId: id }));
  }

  function toggleEducativeMode() {
    update(s => {
      const nextMode = !s.educativeMode;
      if (!nextMode) {
        highlighter.clearHighlights();
      } else {
        highlighter.applyHighlights(s.annotations);
      }
      return { ...s, educativeMode: nextMode };
    });
  }

  return {
    subscribe,
    init,
    addAnnotation,
    updateAnnotation,
    deleteAnnotation,
    toggleResolved,
    setActive,
    toggleEducativeMode,
    highlighter
  };
}

export const annotationStore = createAnnotationStore();
