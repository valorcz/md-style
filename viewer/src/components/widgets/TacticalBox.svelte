<script lang="ts">
  import Icon from '../Icon.svelte';

  export let title: string;
  export let tone: 'threat' | 'defense' | 'telemetry' | 'info' = 'info';
  export let icon: string = '';
  export let items: string[] = [];
  export let description: string = '';
  export let code: string = '';
  export let codeLabel: string = '';

  const toneClassMap: Record<string, string> = {
    defense: 'tactical-tips',
    threat: 'tactical-threat',
    telemetry: 'tactical-telemetry',
    info: 'tactical-info'
  };

  const defaultIconMap: Record<string, string> = {
    defense: 'academic',
    threat: 'alert-circle',
    telemetry: 'layers',
    info: 'lightbulb'
  };

  $: resolvedIcon = icon || defaultIconMap[tone] || 'lightbulb';
</script>

<div class="tactical-box {toneClassMap[tone] || 'tactical-info'}">
  <h4 class="tactical-heading">
    <Icon name={resolvedIcon} size={14} />
    <span>{title}</span>
  </h4>

  {#if description}
    <p class="tactical-desc">{description}</p>
  {/if}

  {#if code}
    <div class="tactical-path">
      {#if codeLabel}
        <span class="path-label">{codeLabel}</span>
      {/if}
      <code>{code}</code>
    </div>
  {/if}

  {#if items && items.length > 0}
    <ul class="tactical-list">
      {#each items as item}
        <li>{item}</li>
      {/each}
    </ul>
  {/if}

  <slot />
</div>

<style>
  .tactical-box {
    border-radius: 6px;
    padding: 0.85rem 1rem;
    font-size: 0.8rem;
    line-height: 1.45;
    margin-bottom: 0.5rem;
  }
  .tactical-heading {
    margin: 0 0 0.5rem 0;
    font-size: 0.82rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .tactical-tips {
    background: rgba(2, 132, 199, 0.1);
    border: 1px solid rgba(56, 189, 248, 0.25);
    border-left: 4px solid #0284c7;
    color: #e0f2fe;
  }
  .tactical-threat {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid rgba(239, 68, 68, 0.25);
    border-left: 4px solid #ef4444;
    color: #fee2e2;
  }
  .tactical-telemetry {
    background: rgba(168, 85, 247, 0.1);
    border: 1px solid rgba(168, 85, 247, 0.25);
    border-left: 4px solid #a855f7;
    color: #f3e8ff;
  }
  .tactical-info {
    background: rgba(245, 158, 11, 0.1);
    border: 1px solid rgba(245, 158, 11, 0.25);
    border-left: 4px solid #f59e0b;
    color: #fef3c7;
  }

  .tactical-tips .tactical-heading { color: #38bdf8; }
  .tactical-threat .tactical-heading { color: #f87171; }
  .tactical-telemetry .tactical-heading { color: #c084fc; }
  .tactical-info .tactical-heading { color: #fbbf24; }

  .tactical-desc {
    margin: 0 0 0.4rem 0;
    font-size: 0.78rem;
    line-height: 1.4;
  }

  .tactical-path {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    margin-top: 0.4rem;
    font-size: 0.76rem;
    flex-wrap: wrap;
  }
  .path-label {
    font-weight: 600;
    opacity: 0.85;
  }
  .tactical-path code {
    font-family: var(--font-mono, monospace);
    font-size: 0.76rem;
    background: rgba(0, 0, 0, 0.25);
    padding: 0.15rem 0.45rem;
    border-radius: 4px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
  }

  .tactical-list {
    margin: 0;
    padding-left: 1.25rem;
  }
  .tactical-list li {
    margin-bottom: 0.35rem;
    font-size: 0.78rem;
  }
  .tactical-list li:last-child {
    margin-bottom: 0;
  }

  /* Light Theme */
  :global([data-theme="light"]) .tactical-tips,
  :global(body.light-theme) .tactical-tips,
  :global(body.theme-forensic-dossier) .tactical-tips {
    background: #f0f9ff;
    border-color: #bae6fd;
    border-left: 4px solid #0284c7;
    color: #0369a1;
  }
  :global([data-theme="light"]) .tactical-threat,
  :global(body.light-theme) .tactical-threat,
  :global(body.theme-forensic-dossier) .tactical-threat {
    background: #fef2f2;
    border-color: #fecaca;
    border-left: 4px solid #ef4444;
    color: #b91c1c;
  }
  :global([data-theme="light"]) .tactical-telemetry,
  :global(body.light-theme) .tactical-telemetry,
  :global(body.theme-forensic-dossier) .tactical-telemetry {
    background: #faf5ff;
    border-color: #e9d5ff;
    border-left: 4px solid #a855f7;
    color: #7e22ce;
  }
  :global([data-theme="light"]) .tactical-info,
  :global(body.light-theme) .tactical-info,
  :global(body.theme-forensic-dossier) .tactical-info {
    background: #fffbeb;
    border-color: #fde68a;
    border-left: 4px solid #d97706;
    color: #b45309;
  }
  :global([data-theme="light"]) .tactical-list,
  :global([data-theme="light"]) .tactical-desc,
  :global(body.light-theme) .tactical-list,
  :global(body.light-theme) .tactical-desc,
  :global(body.theme-forensic-dossier) .tactical-list,
  :global(body.theme-forensic-dossier) .tactical-desc {
    color: #334155;
  }
  :global([data-theme="light"]) .tactical-path code,
  :global(body.light-theme) .tactical-path code,
  :global(body.theme-forensic-dossier) .tactical-path code {
    background: #f1f5f9;
    border-color: #cbd5e1;
    color: #0f172a;
  }
</style>
