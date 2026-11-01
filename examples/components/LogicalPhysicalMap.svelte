<script>
  import { onMount } from 'svelte';

  let { initialFilter = 'all' } = $props();

  let activeFilter = $state(initialFilter);

  function setFilter(f) {
    activeFilter = f;
  }

  // Presenter hotkeys
  function handleKeydown(e) {
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
    if (e.key === '1') setFilter('all');
    else if (e.key === '2') setFilter('procA');
    else if (e.key === '3') setFilter('procB');
    else if (e.key === '4') setFilter('fault');
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });
</script>

<div class="logical-physical-map">
  <!-- Top Action Bar -->
  <div class="map-toolbar">
    <!-- Filter Buttons -->
    <div class="map-btn-group">
      <button
        type="button"
        class="flat-btn"
        class:active={activeFilter === 'all'}
        onclick={() => setFilter('all')}
        title="Shortcut: 1"
      >
        All Mappings
      </button>
      <button
        type="button"
        class="flat-btn"
        class:active={activeFilter === 'procA'}
        onclick={() => setFilter('procA')}
        title="Shortcut: 2"
      >
        Process A (Browser)
      </button>
      <button
        type="button"
        class="flat-btn"
        class:active={activeFilter === 'procB'}
        onclick={() => setFilter('procB')}
        title="Shortcut: 3"
      >
        Process B (Editor)
      </button>
      <button
        type="button"
        class="flat-btn"
        class:active={activeFilter === 'fault'}
        onclick={() => setFilter('fault')}
        title="Shortcut: 4"
      >
        Page Fault &amp; Swap (#PF)
      </button>
    </div>

    <!-- Header Label -->
    <span class="map-header-label">
      MMU Hardware Isolation Map
    </span>
  </div>

  <!-- Main 3-Column Systems Architecture SVG -->
  <svg
    viewBox="0 0 940 300"
    class="map-svg"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <marker id="arr-sky" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <polygon points="0 0.5, 5 3, 0 5.5" fill="var(--comp-proc-a)" />
      </marker>
      <marker id="arr-purple" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <polygon points="0 0.5, 5 3, 0 5.5" fill="var(--comp-proc-b)" />
      </marker>
      <marker id="arr-amber" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <polygon points="0 0.5, 5 3, 0 5.5" fill="var(--comp-swap)" />
      </marker>
    </defs>

    <!-- COLUMN 1: VIRTUAL MEMORY ILLUSION (Processes) -->
    <g transform="translate(10, 8)">
      <text x="110" y="12" text-anchor="middle" class="col-head" fill="var(--comp-text)">1. VIRTUAL ADDRESS SPACE</text>
      <text x="110" y="23" text-anchor="middle" class="col-sub" fill="var(--comp-text-muted)">Per-Process View (0x0000...)</text>

      <!-- Process A Container (Browser) -->
      <g
        transform="translate(0, 30)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      >
        <rect x="0" y="0" width="220" height="116" rx="4" class="svg-block" stroke={activeFilter === 'procA' ? 'var(--comp-proc-a)' : 'var(--comp-border)'} />
        <rect x="0" y="0" width="220" height="20" rx="4" fill="var(--comp-header-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-proc-a)">Process A: Browser</text>
        <text x="212" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-text-muted)">PID 1420</text>

        <!-- Page 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="var(--comp-frame-a-bg)" stroke="var(--comp-border)" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="var(--comp-proc-a)">VPN 0 (0x0040...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--comp-text)">Code (.text)</text>
        </g>

        <!-- Page 1 -->
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="var(--comp-frame-a-bg)" stroke="var(--comp-border)" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="var(--comp-proc-a)">VPN 1 (0x1000...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--comp-text)">Active DOM Tab</text>
        </g>

        <!-- Page 2 (Swapped) -->
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="208" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="8" y="15" class="mono-bold" fill="var(--comp-swap)">VPN 2 (0x2000...)</text>
          <text x="200" y="15" text-anchor="end" class="text-tag" fill="var(--comp-swap)">Idle Tab (Swap)</text>
        </g>
      </g>

      <!-- Process B Container (Text Editor) -->
      <g
        transform="translate(0, 154)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA'}
      >
        <rect x="0" y="0" width="220" height="116" rx="4" class="svg-block" stroke={activeFilter === 'procB' ? 'var(--comp-proc-b)' : 'var(--comp-border)'} />
        <rect x="0" y="0" width="220" height="20" rx="4" fill="var(--comp-header-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-proc-b)">Process B: Editor</text>
        <text x="212" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-text-muted)">PID 2894</text>

        <!-- Page 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="var(--comp-frame-b-bg)" stroke="var(--comp-border)" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="var(--comp-proc-b)">VPN 0 (0x0040...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--comp-text)">Editor Binary</text>
        </g>

        <!-- Page 1 -->
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="var(--comp-frame-b-bg)" stroke="var(--comp-border)" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="var(--comp-proc-b)">VPN 1 (0x1000...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--comp-text)">Doc Buffer</text>
        </g>

        <!-- Page 2 (Swapped) -->
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="208" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="8" y="15" class="mono-bold" fill="var(--comp-swap)">VPN 2 (0x2000...)</text>
          <text x="200" y="15" text-anchor="end" class="text-tag" fill="var(--comp-swap)">Undo Log (Swap)</text>
        </g>
      </g>
    </g>

    <!-- COLUMN 2: TRANSLATION SWITCHBOARD (Page Tables) -->
    <g transform="translate(260, 8)">
      <text x="135" y="12" text-anchor="middle" class="col-head" fill="var(--comp-text)">2. PAGE TABLES (MMU)</text>
      <text x="135" y="23" text-anchor="middle" class="col-sub" fill="var(--comp-text-muted)">Hardware Address Mapping</text>

      <!-- Page Table A -->
      <g
        transform="translate(0, 30)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      >
        <rect x="0" y="0" width="270" height="116" rx="4" class="svg-block" stroke="var(--comp-border)" />
        <rect x="0" y="0" width="270" height="20" rx="4" fill="var(--comp-header-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-text)">Page Table A (CR3_A)</text>
        <text x="262" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-text-muted)">VPN ➔ PFN</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="var(--comp-frame-bg)" stroke="var(--comp-border)" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--comp-text)">[0] ➔ PFN 3</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="var(--comp-proc-a)">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="var(--comp-frame-bg)" stroke="var(--comp-border)" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--comp-text)">[1] ➔ PFN 7</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="var(--comp-proc-a)">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="258" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.7" />
          <text x="8" y="15" class="mono-code" fill="var(--comp-swap)">[2] ➔ Swap #1</text>
          <text x="250" y="15" text-anchor="end" class="mono-badge" fill="var(--comp-swap)">V=0 (#PF)</text>
        </g>
      </g>

      <!-- Page Table B -->
      <g
        transform="translate(0, 154)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA'}
      >
        <rect x="0" y="0" width="270" height="116" rx="4" class="svg-block" stroke="var(--comp-border)" />
        <rect x="0" y="0" width="270" height="20" rx="4" fill="var(--comp-header-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-text)">Page Table B (CR3_B)</text>
        <text x="262" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-text-muted)">VPN ➔ PFN</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="var(--comp-frame-bg)" stroke="var(--comp-border)" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--comp-text)">[0] ➔ PFN 1</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="var(--comp-proc-b)">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="var(--comp-frame-bg)" stroke="var(--comp-border)" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--comp-text)">[1] ➔ PFN 5</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="var(--comp-proc-b)">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="258" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.7" />
          <text x="8" y="15" class="mono-code" fill="var(--comp-swap)">[2] ➔ Swap #2</text>
          <text x="250" y="15" text-anchor="end" class="mono-badge" fill="var(--comp-swap)">V=0 (#PF)</text>
        </g>
      </g>
    </g>

    <!-- CONNECTOR BUS LINES -->
    <g stroke-width="1.2">
      <!-- Proc A -> PT A -->
      <line x1="230" y1="69" x2="260" y2="69" stroke={activeFilter === 'procB' ? 'var(--comp-border)' : 'var(--comp-proc-a)'} marker-end="url(#arr-sky)" />
      <line x1="230" y1="99" x2="260" y2="99" stroke={activeFilter === 'procB' ? 'var(--comp-border)' : 'var(--comp-proc-a)'} marker-end="url(#arr-sky)" />
      <line x1="230" y1="128" x2="260" y2="128" stroke={activeFilter === 'procB' ? 'var(--comp-border)' : 'var(--comp-swap)'} marker-end="url(#arr-amber)" />

      <!-- Proc B -> PT B -->
      <line x1="230" y1="193" x2="260" y2="193" stroke={activeFilter === 'procA' ? 'var(--comp-border)' : 'var(--comp-proc-b)'} marker-end="url(#arr-purple)" />
      <line x1="230" y1="223" x2="260" y2="223" stroke={activeFilter === 'procA' ? 'var(--comp-border)' : 'var(--comp-proc-b)'} marker-end="url(#arr-purple)" />
      <line x1="230" y1="252" x2="260" y2="252" stroke={activeFilter === 'procA' ? 'var(--comp-border)' : 'var(--comp-swap)'} marker-end="url(#arr-amber)" />
    </g>

    <!-- COLUMN 3: PHYSICAL REALITY (DRAM & SSD Pagefile) -->
    <g transform="translate(600, 8)">
      <text x="160" y="12" text-anchor="middle" class="col-head" fill="var(--comp-text)">3. PHYSICAL REALITY</text>
      <text x="160" y="23" text-anchor="middle" class="col-sub" fill="var(--comp-text-muted)">DRAM Frames &amp; Pagefile on Disk</text>

      <!-- DRAM Physical Memory Rack -->
      <g transform="translate(0, 30)">
        <rect x="0" y="0" width="320" height="154" rx="4" class="svg-block" stroke="var(--comp-border)" />
        <rect x="0" y="0" width="320" height="20" rx="4" fill="var(--comp-header-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-text)">Physical RAM (DRAM Frames)</text>
        <text x="312" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-text-muted)">4 KB Granularity</text>

        <!-- Frame 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="var(--comp-frame-bg)" stroke="var(--comp-border)" stroke-width="0.7" />
          <text x="6" y="16" class="mono-code" fill="var(--comp-text-muted)">PFN 0: Kernel</text>
        </g>
        <!-- Frame 1 (B: Binary) -->
        <g transform="translate(160, 26)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="var(--comp-frame-b-bg)" stroke={activeFilter === 'procA' ? 'var(--comp-border)' : 'var(--comp-proc-b)'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procA' ? 'var(--comp-text-muted)' : 'var(--comp-proc-b)'}>PFN 1: B (Editor)</text>
        </g>
        <!-- Frame 3 (A: Engine) -->
        <g transform="translate(6, 58)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="var(--comp-frame-a-bg)" stroke={activeFilter === 'procB' ? 'var(--comp-border)' : 'var(--comp-proc-a)'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procB' ? 'var(--comp-text-muted)' : 'var(--comp-proc-a)'}>PFN 3: A (Browser)</text>
        </g>
        <!-- Frame 5 (B: Doc) -->
        <g transform="translate(160, 58)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="var(--comp-frame-b-bg)" stroke={activeFilter === 'procA' ? 'var(--comp-border)' : 'var(--comp-proc-b)'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procA' ? 'var(--comp-text-muted)' : 'var(--comp-proc-b)'}>PFN 5: B (Buffer)</text>
        </g>
        <!-- Frame 6 (Free Target) -->
        <g transform="translate(6, 90)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="var(--comp-frame-free-bg)" stroke="var(--comp-free)" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="6" y="16" class="mono-code" fill="var(--comp-free)">PFN 6: [Free Page]</text>
        </g>
        <!-- Frame 7 (A: Tab) -->
        <g transform="translate(160, 90)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="var(--comp-frame-a-bg)" stroke={activeFilter === 'procB' ? 'var(--comp-border)' : 'var(--comp-proc-a)'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procB' ? 'var(--comp-text-muted)' : 'var(--comp-proc-a)'}>PFN 7: A (Tab DOM)</text>
        </g>

        <text x="160" y="136" text-anchor="middle" class="svg-meta" fill="var(--comp-text-muted)">
          Physical DRAM contains no concept of processes — only raw frames.
        </text>
      </g>

      <!-- SSD Backing Store / Pagefile -->
      <g transform="translate(0, 194)">
        <rect x="0" y="0" width="320" height="76" rx="4" class="svg-block" stroke="var(--comp-swap)" stroke-width="1" />
        <rect x="0" y="0" width="320" height="20" rx="4" fill="var(--comp-frame-swap-bg)" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--comp-swap)">SSD Backing Store (pagefile.sys / swap)</text>
        <text x="312" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--comp-swap)">Cold Pages</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="148" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.7" />
          <text x="6" y="15" class="mono-code" fill="var(--comp-swap)">Swap #1: A (Idle Tab)</text>
        </g>
        <g transform="translate(160, 26)">
          <rect x="0" y="0" width="154" height="24" rx="3" fill="var(--comp-frame-swap-bg)" stroke="var(--comp-swap)" stroke-width="0.7" />
          <text x="6" y="15" class="mono-code" fill="var(--comp-swap)">Swap #2: B (Undo Log)</text>
        </g>
        <text x="8" y="64" class="svg-meta" fill="var(--comp-text-muted)">
          Accessing V=0 causes #PF exception ➔ OS loads data into Free PFN 6 ➔ sets V=1
        </text>
      </g>
    </g>

    <!-- Orthogonal Bus Connectors from Page Tables to Targets -->
    <g stroke-width="1.2">
      <!-- PT A [0] -> PFN 3 -->
      <path
        d="M 530 69 L 560 69 L 560 98 L 600 98"
        stroke="var(--comp-proc-a)"
        fill="none"
        marker-end="url(#arr-sky)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB' || activeFilter === 'fault'}
      />
      <!-- PT A [1] -> PFN 7 -->
      <path
        d="M 530 99 L 570 99 L 570 130 L 754 130"
        stroke="var(--comp-proc-a)"
        fill="none"
        marker-end="url(#arr-sky)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB' || activeFilter === 'fault'}
      />
      <!-- PT A [2] -> Swap #1 -->
      <path
        d="M 530 128 L 580 128 L 580 232 L 600 232"
        stroke="var(--comp-swap)"
        fill="none"
        marker-end="url(#arr-amber)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      />

      <!-- PT B [0] -> PFN 1 -->
      <path
        d="M 530 193 L 550 193 L 550 66 L 754 66"
        stroke="var(--comp-proc-b)"
        fill="none"
        marker-end="url(#arr-purple)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA' || activeFilter === 'fault'}
      />
      <!-- PT B [1] -> PFN 5 -->
      <path
        d="M 530 223 L 565 223 L 565 98 L 754 98"
        stroke="var(--comp-proc-b)"
        fill="none"
        marker-end="url(#arr-purple)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA' || activeFilter === 'fault'}
      />
      <!-- PT B [2] -> Swap #2 -->
      <path
        d="M 530 252 L 590 252 L 590 232 L 754 232"
        stroke="var(--comp-swap)"
        fill="none"
        marker-end="url(#arr-amber)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA'}
      />
    </g>
  </svg>

  <!-- Status Bar Footer -->
  <div class="map-status-bar">
    <div class="status-summary">
      <span class="status-label">Address Isolation:</span>
      <span>
        Both processes access virtual <strong style="color: var(--comp-proc-a);">0x00400000</strong>
        ➔ MMU maps to distinct DRAM:
        <span style="color: var(--comp-proc-a); font-weight: 600;">A: PFN 3</span> vs.
        <span style="color: var(--comp-proc-b); font-weight: 600;">B: PFN 1</span>
      </span>
    </div>
    <div class="status-sub">
      Evicted pages (V=0) reside in pagefile.sys
    </div>
  </div>
</div>

<style>
  .logical-physical-map {
    display: flex;
    flex-direction: column;
    align-items: center;
    width: 100%;
    margin: 1.5rem 0;
    user-select: none;
    font-family: var(--font-sans, system-ui, sans-serif);

    /* Light Theme Palette Tokens (High Contrast, Publication Grade) */
    --comp-proc-a: #0284c7;
    --comp-proc-b: #7c3aed;
    --comp-swap: #b45309;
    --comp-free: #059669;
    --comp-surface: var(--color-paper, #ffffff);
    --comp-surface-subtle: var(--color-bg, #f8fafc);
    --comp-header-bg: rgba(0, 0, 0, 0.035);
    --comp-border: var(--color-border, #e2e8f0);
    --comp-border-strong: var(--color-border-dark, #cbd5e1);
    --comp-text: var(--color-text, #0f172a);
    --comp-text-muted: var(--color-text-muted, #64748b);
    --comp-frame-bg: rgba(0, 0, 0, 0.02);
    --comp-frame-a-bg: rgba(2, 132, 199, 0.07);
    --comp-frame-b-bg: rgba(124, 58, 237, 0.07);
    --comp-frame-swap-bg: rgba(180, 83, 9, 0.07);
    --comp-frame-free-bg: rgba(5, 150, 105, 0.07);
  }

  /* Dark Theme Palette Tokens (Vibrant & Deep Obsidian) */
  :global([data-theme="dark"]) .logical-physical-map,
  :global(body.dark-theme) .logical-physical-map,
  :global(body.theme-forensic-cyber) .logical-physical-map {
    --comp-proc-a: #38bdf8;
    --comp-proc-b: #a78bfa;
    --comp-swap: #fbbf24;
    --comp-free: #34d399;
    --comp-surface: rgba(15, 23, 42, 0.85);
    --comp-surface-subtle: rgba(15, 23, 42, 0.6);
    --comp-header-bg: rgba(255, 255, 255, 0.06);
    --comp-border: rgba(255, 255, 255, 0.14);
    --comp-border-strong: rgba(255, 255, 255, 0.25);
    --comp-text: #f1f5f9;
    --comp-text-muted: #94a3b8;
    --comp-frame-bg: rgba(255, 255, 255, 0.02);
    --comp-frame-a-bg: rgba(56, 189, 248, 0.12);
    --comp-frame-b-bg: rgba(167, 139, 250, 0.12);
    --comp-frame-swap-bg: rgba(251, 191, 36, 0.12);
    --comp-frame-free-bg: rgba(52, 211, 153, 0.12);
  }

  .map-toolbar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    width: 100%;
    max-width: 940px;
    margin-bottom: 0.5rem;
  }

  .map-btn-group {
    display: flex;
    align-items: center;
    gap: 0.375rem;
    flex-wrap: wrap;
  }

  .flat-btn {
    display: inline-flex;
    align-items: center;
    padding: 3px 9px;
    border-radius: 4px;
    font-size: 10px;
    font-weight: 600;
    font-family: var(--font-mono, monospace);
    border: 1px solid var(--comp-border-strong);
    background: var(--comp-surface);
    color: var(--comp-text-muted);
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  }

  .flat-btn:hover {
    border-color: var(--comp-proc-a);
    color: var(--comp-text);
  }

  .flat-btn.active {
    background: var(--comp-frame-a-bg);
    border-color: var(--comp-proc-a);
    color: var(--comp-proc-a);
  }

  .map-header-label {
    font-size: 10.5px;
    font-family: var(--font-mono, monospace);
    color: var(--comp-text-muted);
  }

  .map-svg {
    width: 100%;
    max-width: 940px;
    height: auto;
  }

  .map-status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    max-width: 940px;
    padding: 6px 12px;
    border-radius: 4px;
    border: 1px solid var(--comp-border);
    background: var(--comp-surface-subtle);
    font-family: var(--font-mono, monospace);
    font-size: 10px;
    color: var(--comp-text);
    box-sizing: border-box;
    margin-top: 0.5rem;
  }

  .status-summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .status-label {
    color: var(--comp-text-muted);
  }

  .status-sub {
    color: var(--comp-text-muted);
    font-size: 9.5px;
  }

  .anim-fade {
    transition: opacity 0.2s ease;
  }

  .dimmed {
    opacity: 0.18 !important;
  }

  .svg-block {
    fill: var(--comp-surface);
  }

  .col-head {
    font-family: var(--font-mono, monospace);
    font-size: 10px !important;
    font-weight: 700 !important;
    letter-spacing: 0.05em;
  }

  .col-sub {
    font-family: var(--font-mono, monospace);
    font-size: 8px !important;
  }

  .svg-proc-name {
    font-family: var(--font-mono, monospace);
    font-size: 9px !important;
    font-weight: 700 !important;
  }

  .svg-proc-pid {
    font-family: var(--font-mono, monospace);
    font-size: 8.5px !important;
  }

  .mono-bold {
    font-family: var(--font-mono, monospace);
    font-size: 8.5px !important;
    font-weight: 600 !important;
  }

  .mono-code {
    font-family: var(--font-mono, monospace);
    font-size: 8.5px !important;
  }

  .mono-badge {
    font-family: var(--font-mono, monospace);
    font-size: 8px !important;
    font-weight: 700 !important;
  }

  .text-tag {
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 8.5px !important;
  }

  .svg-meta {
    font-family: var(--font-sans, system-ui, sans-serif);
    font-size: 8px !important;
  }

  /* Wide Breakout Responsiveness */
  :global(figure.wide) .logical-physical-map,
  :global(figure.wide) .map-toolbar,
  :global(figure.wide) .map-svg,
  :global(figure.wide) .map-status-bar {
    max-width: 100% !important;
  }
</style>
