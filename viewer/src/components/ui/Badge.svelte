<script lang="ts">
  import Icon from '../Icon.svelte';

  export let variant: 'subtle' | 'outline' | 'solid' = 'subtle';
  export let size: 'sm' | 'md' = 'sm';
  export let color: string = '';
  export let icon: string = '';
  export let title: string = '';

  let clazz: string = '';
  export { clazz as class };
</script>

<span
  class="ui-badge variant-{variant} size-{size} {clazz}"
  style={color ? `--badge-accent: ${color};` : ''}
  {title}
>{#if icon}<Icon name={icon} size={size === 'sm' ? 11 : 13} />{/if}<slot /></span>

<style>
  .ui-badge {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    font-family: inherit;
    font-weight: 600;
    line-height: 1;
    border-radius: 4px;
    letter-spacing: 0.03em;
    user-select: none;
    box-sizing: border-box;
    white-space: nowrap;
  }

  .ui-badge.size-sm {
    padding: 0.15rem 0.4rem;
    font-size: 0.65rem;
  }

  .ui-badge.size-md {
    padding: 0.25rem 0.55rem;
    font-size: 0.72rem;
  }

  /* Variant: Subtle (default) */
  .ui-badge.variant-subtle {
    background: var(--badge-accent, rgba(0, 0, 0, 0.06));
    color: var(--color-text, #334155);
  }

  /* When a color is provided, subtle tint */
  .ui-badge.variant-subtle[style*="--badge-accent"] {
    background: color-mix(in srgb, var(--badge-accent) 12%, transparent);
    color: var(--badge-accent);
  }

  /* Variant: Outline */
  .ui-badge.variant-outline {
    background: transparent;
    border: 1px solid var(--badge-accent, var(--color-border, rgba(0, 0, 0, 0.15)));
    color: var(--badge-accent, var(--color-text-muted, #64748b));
  }

  /* Variant: Solid */
  .ui-badge.variant-solid {
    background: var(--badge-accent, #0284c7);
    color: #ffffff;
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .ui-badge.variant-subtle:not([style*="--badge-accent"]),
  :global(body.theme-cyber) .ui-badge.variant-subtle:not([style*="--badge-accent"]),
  :global(body.dark-theme) .ui-badge.variant-subtle:not([style*="--badge-accent"]) {
    background: rgba(255, 255, 255, 0.1);
    color: #e2e8f0;
  }

  :global([data-theme="dark"]) .ui-badge.variant-outline:not([style*="--badge-accent"]),
  :global(body.theme-cyber) .ui-badge.variant-outline:not([style*="--badge-accent"]),
  :global(body.dark-theme) .ui-badge.variant-outline:not([style*="--badge-accent"]) {
    border-color: rgba(255, 255, 255, 0.2);
    color: #94a3b8;
  }
</style>
