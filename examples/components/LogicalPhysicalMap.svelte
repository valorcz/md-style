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
        <polygon points="0 0.5, 5 3, 0 5.5" fill="#38bdf8" />
      </marker>
      <marker id="arr-purple" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <polygon points="0 0.5, 5 3, 0 5.5" fill="#a78bfa" />
      </marker>
      <marker id="arr-amber" markerWidth="6" markerHeight="6" refX="5" refY="3" orient="auto">
        <polygon points="0 0.5, 5 3, 0 5.5" fill="#fbbf24" />
      </marker>
    </defs>

    <!-- COLUMN 1: VIRTUAL MEMORY ILLUSION (Processes) -->
    <g transform="translate(10, 8)">
      <text x="110" y="12" text-anchor="middle" class="col-head" fill="var(--fg, #e2e8f0)">1. VIRTUAL ADDRESS SPACE</text>
      <text x="110" y="23" text-anchor="middle" class="col-sub" fill="var(--fg-dim, #94a3b8)">Per-Process View (0x0000...)</text>

      <!-- Process A Container (Browser) -->
      <g
        transform="translate(0, 30)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      >
        <rect x="0" y="0" width="220" height="116" rx="4" class="svg-block" stroke={activeFilter === 'procA' ? '#38bdf8' : 'var(--line, rgba(255,255,255,0.15))'} />
        <rect x="0" y="0" width="220" height="20" rx="4" fill="var(--line, rgba(255,255,255,0.08))" />
        <text x="8" y="14" class="svg-proc-name" fill="#38bdf8">Process A: Browser</text>
        <text x="212" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--fg-dim, #94a3b8)">PID 1420</text>

        <!-- Page 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="#38bdf8">VPN 0 (0x0040...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--fg, #e2e8f0)">Code (.text)</text>
        </g>

        <!-- Page 1 -->
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="#38bdf8">VPN 1 (0x1000...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--fg, #e2e8f0)">Active DOM Tab</text>
        </g>

        <!-- Page 2 (Swapped) -->
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="208" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="8" y="15" class="mono-bold" fill="#fbbf24">VPN 2 (0x2000...)</text>
          <text x="200" y="15" text-anchor="end" class="text-tag" fill="#fbbf24">Idle Tab (Swap)</text>
        </g>
      </g>

      <!-- Process B Container (Text Editor) -->
      <g
        transform="translate(0, 154)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA'}
      >
        <rect x="0" y="0" width="220" height="116" rx="4" class="svg-block" stroke={activeFilter === 'procB' ? '#a78bfa' : 'var(--line, rgba(255,255,255,0.15))'} />
        <rect x="0" y="0" width="220" height="20" rx="4" fill="var(--line, rgba(255,255,255,0.08))" />
        <text x="8" y="14" class="svg-proc-name" fill="#a78bfa">Process B: Editor</text>
        <text x="212" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--fg-dim, #94a3b8)">PID 2894</text>

        <!-- Page 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="#a78bfa">VPN 0 (0x0040...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--fg, #e2e8f0)">Editor Binary</text>
        </g>

        <!-- Page 1 -->
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="208" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.8" />
          <text x="8" y="16" class="mono-bold" fill="#a78bfa">VPN 1 (0x1000...)</text>
          <text x="200" y="16" text-anchor="end" class="text-tag" fill="var(--fg, #e2e8f0)">Doc Buffer</text>
        </g>

        <!-- Page 2 (Swapped) -->
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="208" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="8" y="15" class="mono-bold" fill="#fbbf24">VPN 2 (0x2000...)</text>
          <text x="200" y="15" text-anchor="end" class="text-tag" fill="#fbbf24">Undo Log (Swap)</text>
        </g>
      </g>
    </g>

    <!-- COLUMN 2: TRANSLATION SWITCHBOARD (Page Tables) -->
    <g transform="translate(260, 8)">
      <text x="135" y="12" text-anchor="middle" class="col-head" fill="var(--fg, #e2e8f0)">2. PAGE TABLES (MMU)</text>
      <text x="135" y="23" text-anchor="middle" class="col-sub" fill="var(--fg-dim, #94a3b8)">Hardware Address Mapping</text>

      <!-- Page Table A -->
      <g
        transform="translate(0, 30)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      >
        <rect x="0" y="0" width="270" height="116" rx="4" class="svg-block" stroke="var(--line, rgba(255,255,255,0.15))" />
        <rect x="0" y="0" width="270" height="20" rx="4" fill="var(--line, rgba(255,255,255,0.08))" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--fg, #e2e8f0)">Page Table A (CR3_A)</text>
        <text x="262" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--fg-dim, #94a3b8)">VPN ➔ PFN</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--fg, #e2e8f0)">[0] ➔ PFN 3</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="#38bdf8">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--fg, #e2e8f0)">[1] ➔ PFN 7</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="#38bdf8">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="258" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.7" />
          <text x="8" y="15" class="mono-code" fill="#fbbf24">[2] ➔ Swap #1</text>
          <text x="250" y="15" text-anchor="end" class="mono-badge" fill="#fbbf24">V=0 (#PF)</text>
        </g>
      </g>

      <!-- Page Table B -->
      <g
        transform="translate(0, 154)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA'}
      >
        <rect x="0" y="0" width="270" height="116" rx="4" class="svg-block" stroke="var(--line, rgba(255,255,255,0.15))" />
        <rect x="0" y="0" width="270" height="20" rx="4" fill="var(--line, rgba(255,255,255,0.08))" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--fg, #e2e8f0)">Page Table B (CR3_B)</text>
        <text x="262" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--fg-dim, #94a3b8)">VPN ➔ PFN</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--fg, #e2e8f0)">[0] ➔ PFN 1</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="#a78bfa">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 56)">
          <rect x="0" y="0" width="258" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.7" />
          <text x="8" y="16" class="mono-code" fill="var(--fg, #e2e8f0)">[1] ➔ PFN 5</text>
          <text x="250" y="16" text-anchor="end" class="mono-badge" fill="#a78bfa">V=1 (RAM)</text>
        </g>
        <g transform="translate(6, 86)">
          <rect x="0" y="0" width="258" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.7" />
          <text x="8" y="15" class="mono-code" fill="#fbbf24">[2] ➔ Swap #2</text>
          <text x="250" y="15" text-anchor="end" class="mono-badge" fill="#fbbf24">V=0 (#PF)</text>
        </g>
      </g>
    </g>

    <!-- CONNECTOR BUS LINES -->
    <g stroke-width="1.2">
      <!-- Proc A -> PT A -->
      <line x1="230" y1="69" x2="260" y2="69" stroke={activeFilter === 'procB' ? 'var(--line, rgba(255,255,255,0.15))' : '#38bdf8'} marker-end="url(#arr-sky)" />
      <line x1="230" y1="99" x2="260" y2="99" stroke={activeFilter === 'procB' ? 'var(--line, rgba(255,255,255,0.15))' : '#38bdf8'} marker-end="url(#arr-sky)" />
      <line x1="230" y1="128" x2="260" y2="128" stroke={activeFilter === 'procB' ? 'var(--line, rgba(255,255,255,0.15))' : '#fbbf24'} marker-end="url(#arr-amber)" />

      <!-- Proc B -> PT B -->
      <line x1="230" y1="193" x2="260" y2="193" stroke={activeFilter === 'procA' ? 'var(--line, rgba(255,255,255,0.15))' : '#a78bfa'} marker-end="url(#arr-purple)" />
      <line x1="230" y1="223" x2="260" y2="223" stroke={activeFilter === 'procA' ? 'var(--line, rgba(255,255,255,0.15))' : '#a78bfa'} marker-end="url(#arr-purple)" />
      <line x1="230" y1="252" x2="260" y2="252" stroke={activeFilter === 'procA' ? 'var(--line, rgba(255,255,255,0.15))' : '#fbbf24'} marker-end="url(#arr-amber)" />
    </g>

    <!-- COLUMN 3: PHYSICAL REALITY (DRAM & SSD Pagefile) -->
    <g transform="translate(600, 8)">
      <text x="160" y="12" text-anchor="middle" class="col-head" fill="var(--fg, #e2e8f0)">3. PHYSICAL REALITY</text>
      <text x="160" y="23" text-anchor="middle" class="col-sub" fill="var(--fg-dim, #94a3b8)">DRAM Frames &amp; Pagefile on Disk</text>

      <!-- DRAM Physical Memory Rack -->
      <g transform="translate(0, 30)">
        <rect x="0" y="0" width="320" height="154" rx="4" class="svg-block" stroke="var(--line, rgba(255,255,255,0.15))" />
        <rect x="0" y="0" width="320" height="20" rx="4" fill="var(--line, rgba(255,255,255,0.08))" />
        <text x="8" y="14" class="svg-proc-name" fill="var(--fg, #e2e8f0)">Physical RAM (DRAM Frames)</text>
        <text x="312" y="14" text-anchor="end" class="svg-proc-pid" fill="var(--fg-dim, #94a3b8)">4 KB Granularity</text>

        <!-- Frame 0 -->
        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="rgba(255, 255, 255, 0.02)" stroke="var(--line, rgba(255,255,255,0.15))" stroke-width="0.7" />
          <text x="6" y="16" class="mono-code" fill="var(--fg-dim, #94a3b8)">PFN 0: Kernel</text>
        </g>
        <!-- Frame 1 (B: Binary) -->
        <g transform="translate(160, 26)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="rgba(167, 139, 250, 0.08)" stroke={activeFilter === 'procA' ? 'var(--line, rgba(255,255,255,0.15))' : '#a78bfa'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procA' ? 'var(--fg-dim, #94a3b8)' : '#a78bfa'}>PFN 1: B (Editor)</text>
        </g>
        <!-- Frame 3 (A: Engine) -->
        <g transform="translate(6, 58)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="rgba(56, 189, 248, 0.08)" stroke={activeFilter === 'procB' ? 'var(--line, rgba(255,255,255,0.15))' : '#38bdf8'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procB' ? 'var(--fg-dim, #94a3b8)' : '#38bdf8'}>PFN 3: A (Browser)</text>
        </g>
        <!-- Frame 5 (B: Doc) -->
        <g transform="translate(160, 58)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="rgba(167, 139, 250, 0.08)" stroke={activeFilter === 'procA' ? 'var(--line, rgba(255,255,255,0.15))' : '#a78bfa'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procA' ? 'var(--fg-dim, #94a3b8)' : '#a78bfa'}>PFN 5: B (Buffer)</text>
        </g>
        <!-- Frame 6 (Free Target) -->
        <g transform="translate(6, 90)">
          <rect x="0" y="0" width="148" height="26" rx="3" fill="rgba(16, 185, 129, 0.06)" stroke="#10b981" stroke-width="0.8" stroke-dasharray="3 2" />
          <text x="6" y="16" class="mono-code" fill="#10b981">PFN 6: [Free Page]</text>
        </g>
        <!-- Frame 7 (A: Tab) -->
        <g transform="translate(160, 90)">
          <rect x="0" y="0" width="154" height="26" rx="3" fill="rgba(56, 189, 248, 0.08)" stroke={activeFilter === 'procB' ? 'var(--line, rgba(255,255,255,0.15))' : '#38bdf8'} stroke-width="0.8" />
          <text x="6" y="16" class="mono-code" fill={activeFilter === 'procB' ? 'var(--fg-dim, #94a3b8)' : '#38bdf8'}>PFN 7: A (Tab DOM)</text>
        </g>

        <text x="160" y="136" text-anchor="middle" class="svg-meta" fill="var(--fg-dim, #94a3b8)">
          Physical DRAM contains no concept of processes — only raw frames.
        </text>
      </g>

      <!-- SSD Backing Store / Pagefile -->
      <g transform="translate(0, 194)">
        <rect x="0" y="0" width="320" height="76" rx="4" class="svg-block" stroke="#fbbf24" stroke-width="1" />
        <rect x="0" y="0" width="320" height="20" rx="4" fill="rgba(251, 191, 36, 0.15)" />
        <text x="8" y="14" class="svg-proc-name" fill="#fbbf24">SSD Backing Store (pagefile.sys / swap)</text>
        <text x="312" y="14" text-anchor="end" class="svg-proc-pid" fill="#fbbf24">Cold Pages</text>

        <g transform="translate(6, 26)">
          <rect x="0" y="0" width="148" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.7" />
          <text x="6" y="15" class="mono-code" fill="#fbbf24">Swap #1: A (Idle Tab)</text>
        </g>
        <g transform="translate(160, 26)">
          <rect x="0" y="0" width="154" height="24" rx="3" fill="rgba(251, 191, 36, 0.06)" stroke="#fbbf24" stroke-width="0.7" />
          <text x="6" y="15" class="mono-code" fill="#fbbf24">Swap #2: B (Undo Log)</text>
        </g>
        <text x="8" y="64" class="svg-meta" fill="var(--fg-dim, #94a3b8)">
          Accessing V=0 causes #PF exception ➔ OS loads data into Free PFN 6 ➔ sets V=1
        </text>
      </g>
    </g>

    <!-- Orthogonal Bus Connectors from Page Tables to Targets -->
    <g stroke-width="1.2">
      <!-- PT A [0] -> PFN 3 -->
      <path
        d="M 530 69 L 560 69 L 560 98 L 600 98"
        stroke="#38bdf8"
        fill="none"
        marker-end="url(#arr-sky)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB' || activeFilter === 'fault'}
      />
      <!-- PT A [1] -> PFN 7 -->
      <path
        d="M 530 99 L 570 99 L 570 130 L 754 130"
        stroke="#38bdf8"
        fill="none"
        marker-end="url(#arr-sky)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB' || activeFilter === 'fault'}
      />
      <!-- PT A [2] -> Swap #1 -->
      <path
        d="M 530 128 L 580 128 L 580 232 L 600 232"
        stroke="#fbbf24"
        fill="none"
        marker-end="url(#arr-amber)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procB'}
      />

      <!-- PT B [0] -> PFN 1 -->
      <path
        d="M 530 193 L 550 193 L 550 66 L 754 66"
        stroke="#a78bfa"
        fill="none"
        marker-end="url(#arr-purple)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA' || activeFilter === 'fault'}
      />
      <!-- PT B [1] -> PFN 5 -->
      <path
        d="M 530 223 L 565 223 L 565 98 L 754 98"
        stroke="#a78bfa"
        fill="none"
        marker-end="url(#arr-purple)"
        class="anim-fade"
        class:dimmed={activeFilter === 'procA' || activeFilter === 'fault'}
      />
      <!-- PT B [2] -> Swap #2 -->
      <path
        d="M 530 252 L 590 252 L 590 232 L 754 232"
        stroke="#fbbf24"
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
        Both processes access virtual <strong style="color: #38bdf8;">0x00400000</strong>
        ➔ MMU maps to distinct DRAM:
        <span style="color: #38bdf8;">A: PFN 3</span> vs.
        <span style="color: #a78bfa;">B: PFN 1</span>
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
    border: 1px solid var(--line, rgba(255, 255, 255, 0.15));
    background: var(--surface-bg, rgba(15, 23, 42, 0.6));
    color: var(--fg-dim, #94a3b8);
    cursor: pointer;
    transition: all 0.15s ease;
    box-shadow: 0 1px 2px rgba(0, 0, 0, 0.15);
  }

  .flat-btn:hover {
    border-color: #38bdf8;
    color: var(--fg, #ffffff);
  }

  .flat-btn.active {
    background: rgba(56, 189, 248, 0.15);
    border-color: #38bdf8;
    color: #38bdf8;
  }

  .map-header-label {
    font-size: 10.5px;
    font-family: var(--font-mono, monospace);
    color: var(--fg-dim, #94a3b8);
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
    border: 1px solid var(--line, rgba(255, 255, 255, 0.15));
    background: var(--surface-bg, rgba(15, 23, 42, 0.6));
    font-family: var(--font-mono, monospace);
    font-size: 10px;
    box-sizing: border-box;
    margin-top: 0.5rem;
  }

  .status-summary {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .status-label {
    color: var(--fg-dim, #94a3b8);
  }

  .status-sub {
    color: var(--fg-dim, #94a3b8);
    font-size: 9.5px;
  }

  .anim-fade {
    transition: opacity 0.2s ease;
  }

  .dimmed {
    opacity: 0.15 !important;
  }

  .svg-block {
    fill: var(--surface-bg, rgba(15, 23, 42, 0.8));
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
</style>
