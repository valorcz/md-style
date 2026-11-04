<script lang="ts">
  import Icon from '../Icon.svelte';

  export let variant: 'primary' | 'secondary' | 'ghost' | 'danger' = 'secondary';
  export let size: 'sm' | 'md' = 'sm';
  export let icon: string = '';
  export let iconRight: boolean = false;
  export let disabled: boolean = false;
  export let title: string = '';
  export let ariaLabel: string = '';
  export let type: 'button' | 'submit' = 'button';

  let clazz: string = '';
  export { clazz as class };
</script>

<button
  {type}
  class="ui-btn variant-{variant} size-{size} {clazz}"
  {disabled}
  {title}
  aria-label={ariaLabel || title}
  on:click
  on:keydown
>
  {#if icon && !iconRight}
    <Icon name={icon} size={size === 'sm' ? 12 : 14} />
  {/if}
  <slot />
  {#if icon && iconRight}
    <Icon name={icon} size={size === 'sm' ? 12 : 14} />
  {/if}
</button>

<style>
  .ui-btn {
    appearance: none;
    -webkit-appearance: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    margin: 0;
    font-family: inherit;
    font-weight: 500;
    line-height: 1.2;
    border-radius: 4px;
    cursor: pointer;
    box-sizing: border-box;
    transition: all 0.14s ease;
    user-select: none;
    white-space: nowrap;
    text-decoration: none;
  }

  .ui-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
    pointer-events: none;
  }

  .ui-btn:focus-visible {
    outline: 2px solid var(--color-accent, #0284c7);
    outline-offset: 1px;
  }

  /* Sizes */
  .ui-btn.size-sm {
    padding: 0.25rem 0.55rem;
    font-size: 0.72rem;
  }

  .ui-btn.size-md {
    padding: 0.4rem 0.85rem;
    font-size: 0.82rem;
  }

  /* Variant: Secondary (Default) */
  .ui-btn.variant-secondary {
    background: rgba(0, 0, 0, 0.04);
    border: 1px solid var(--color-border, rgba(0, 0, 0, 0.12));
    color: var(--color-text, #334155);
  }
  .ui-btn.variant-secondary:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.08);
    color: var(--color-text, #0f172a);
    border-color: rgba(0, 0, 0, 0.2);
  }

  /* Variant: Primary */
  .ui-btn.variant-primary {
    background: var(--color-accent, #0284c7);
    border: 1px solid transparent;
    color: #ffffff;
    box-shadow: 0 1px 2px rgba(2, 132, 199, 0.3);
  }
  .ui-btn.variant-primary:hover:not(:disabled) {
    background: #0369a1;
  }

  /* Variant: Ghost */
  .ui-btn.variant-ghost {
    background: transparent;
    border: 1px solid transparent;
    color: var(--color-text-muted, #64748b);
  }
  .ui-btn.variant-ghost:hover:not(:disabled) {
    background: rgba(0, 0, 0, 0.05);
    color: var(--color-text, #0f172a);
  }

  /* Variant: Danger */
  .ui-btn.variant-danger {
    background: rgba(239, 68, 68, 0.08);
    border: 1px solid rgba(239, 68, 68, 0.2);
    color: #dc2626;
  }
  .ui-btn.variant-danger:hover:not(:disabled) {
    background: rgba(239, 68, 68, 0.18);
    color: #b91c1c;
  }

  /* Dark Theme */
  :global([data-theme="dark"]) .ui-btn.variant-secondary,
  :global(body.theme-cyber) .ui-btn.variant-secondary,
  :global(body.dark-theme) .ui-btn.variant-secondary {
    background: rgba(255, 255, 255, 0.06);
    border-color: rgba(255, 255, 255, 0.12);
    color: #e2e8f0;
  }
  :global([data-theme="dark"]) .ui-btn.variant-secondary:hover:not(:disabled),
  :global(body.theme-cyber) .ui-btn.variant-secondary:hover:not(:disabled),
  :global(body.dark-theme) .ui-btn.variant-secondary:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.12);
    color: #ffffff;
    border-color: rgba(255, 255, 255, 0.25);
  }

  :global([data-theme="dark"]) .ui-btn.variant-ghost,
  :global(body.theme-cyber) .ui-btn.variant-ghost,
  :global(body.dark-theme) .ui-btn.variant-ghost {
    color: #94a3b8;
  }
  :global([data-theme="dark"]) .ui-btn.variant-ghost:hover:not(:disabled),
  :global(body.theme-cyber) .ui-btn.variant-ghost:hover:not(:disabled),
  :global(body.dark-theme) .ui-btn.variant-ghost:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.08);
    color: #ffffff;
  }
</style>
