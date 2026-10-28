<script lang="ts">
  import Icon from '../Icon.svelte';

  export let title: string = 'MITRE CWE TOP 25 MOST DANGEROUS WEAKNESSES';
  export let rank: number | string = 1;
</script>

<div class="cwe-rank-badge">
  <span class="rank-trophy">
    <Icon name="award" size={20} />
  </span>
  <div class="rank-meta">
    <strong>{title}</strong>
    <span class="rank-position">OFFICIAL RANK #{rank}</span>
  </div>
</div>

<style>
  .cwe-rank-badge {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem 1rem;
    background: rgba(245, 158, 11, 0.12);
    border: 1px solid rgba(245, 158, 11, 0.35);
    border-radius: 6px;
    margin-bottom: 0.5rem;
  }
  .rank-trophy {
    color: #f59e0b;
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .rank-meta {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }
  .rank-meta strong {
    font-size: 0.78rem;
    font-weight: 700;
    color: #fbbf24;
    letter-spacing: 0.04em;
  }
  .rank-position {
    font-size: 0.74rem;
    font-weight: 800;
    color: #f59e0b;
    font-family: var(--font-mono, monospace);
  }

  :global([data-theme="light"]) .cwe-rank-badge,
  :global(body.light-theme) .cwe-rank-badge,
  :global(body.theme-forensic-dossier) .cwe-rank-badge {
    background: #fffbeb;
    border-color: #fde68a;
  }
  :global([data-theme="light"]) .rank-meta strong,
  :global(body.light-theme) .rank-meta strong,
  :global(body.theme-forensic-dossier) .rank-meta strong {
    color: #b45309;
  }
  :global([data-theme="light"]) .rank-position,
  :global(body.light-theme) .rank-position,
  :global(body.theme-forensic-dossier) .rank-position {
    color: #92400e;
  }
</style>
