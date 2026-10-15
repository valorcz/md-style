<script lang="ts">
  export let score: number | string = 0;
  export let severity: string = 'CVSS SEVERITY';
  export let vector: string = '';

  function getCvssClass(s: any): string {
    const num = parseFloat(s);
    if (isNaN(num)) return 'info';
    if (num >= 9.0) return 'critical';
    if (num >= 7.0) return 'high';
    if (num >= 4.0) return 'medium';
    return 'low';
  }
</script>

<div class="cvss-hero-gauge cvss-{getCvssClass(score)}">
  <div class="gauge-left">
    <span class="gauge-score">{score}</span>
    <span class="gauge-scale">/ 10.0</span>
  </div>
  <div class="gauge-info">
    <strong class="gauge-label">{severity}</strong>
    {#if vector}
      <code class="gauge-vector">{vector}</code>
    {/if}
  </div>
</div>

<style>
  .cvss-hero-gauge {
    display: flex;
    align-items: center;
    gap: 1.25rem;
    padding: 0.85rem 1.15rem;
    border-radius: 8px;
    background: rgba(0, 0, 0, 0.25);
    border: 1px solid rgba(255, 255, 255, 0.1);
  }
  .cvss-critical { border-left: 5px solid #ef4444; }
  .cvss-high { border-left: 5px solid #f97316; }
  .cvss-medium { border-left: 5px solid #eab308; }
  .cvss-low { border-left: 5px solid #10b981; }
  .cvss-info { border-left: 5px solid #38bdf8; }

  .gauge-left {
    display: flex;
    align-items: baseline;
    gap: 0.25rem;
  }
  .gauge-score {
    font-size: 1.8rem;
    font-weight: 800;
    line-height: 1;
    font-family: var(--font-mono, monospace);
  }
  .cvss-critical .gauge-score { color: #ef4444; }
  .cvss-high .gauge-score { color: #f97316; }
  .cvss-medium .gauge-score { color: #eab308; }
  .cvss-low .gauge-score { color: #10b981; }
  .cvss-info .gauge-score { color: #38bdf8; }

  .gauge-scale {
    font-size: 0.8rem;
    color: #64748b;
  }
  .gauge-info {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    overflow: hidden;
  }
  .gauge-label {
    font-size: 0.8rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    color: #f8fafc;
    text-transform: uppercase;
  }
  .gauge-vector {
    font-size: 0.7rem;
    font-family: var(--font-mono, monospace);
    color: #94a3b8;
    background: rgba(255, 255, 255, 0.05);
    padding: 0.15rem 0.4rem;
    border-radius: 3px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  :global([data-theme="light"]) .cvss-hero-gauge,
  :global(body.light-theme) .cvss-hero-gauge,
  :global(body.theme-forensic-dossier) .cvss-hero-gauge {
    background: rgba(0, 0, 0, 0.03);
    border: 1px solid rgba(0, 0, 0, 0.08);
  }
  :global([data-theme="light"]) .gauge-label,
  :global(body.light-theme) .gauge-label,
  :global(body.theme-forensic-dossier) .gauge-label {
    color: #0f172a;
  }
</style>
