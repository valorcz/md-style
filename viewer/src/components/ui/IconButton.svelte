<script lang="ts">
  import Icon from '../Icon.svelte';

  export let name: string;
  export let size: number = 14;
  export let title: string = '';
  export let ariaLabel: string = '';
  export let variant: 'ghost' | 'outline' = 'ghost';
  export let active: boolean = false;
  let clazz: string = '';
  export { clazz as class };
</script>

<button
  type="button"
  class="ui-icon-btn variant-{variant} {clazz}"
  class:is-active={active}
  {title}
  aria-label={ariaLabel || title}
  on:click
  on:keydown
>
  <Icon {name} {size} />
</button>

<style>
  .ui-icon-btn {
    appearance: none;
    -webkit-appearance: none;
    background: transparent;
    border: none;
    outline: none;
    box-shadow: none;
    color: var(--color-text-muted, #64748b);
    cursor: pointer;
    padding: 0.25rem 0.4rem;
    margin: 0;
    border-radius: 4px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .ui-icon-btn:hover {
    background: rgba(0, 0, 0, 0.05);
    color: var(--color-text, #0f172a);
  }

  .ui-icon-btn:focus-visible {
    outline: 2px solid var(--color-accent, #0284c7);
    outline-offset: 1px;
  }

  .ui-icon-btn.variant-outline {
    border: 1px solid var(--color-border, #e2e8f0);
  }

  :global([data-theme="dark"]) .ui-icon-btn,
  :global(body.theme-cyber) .ui-icon-btn {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .ui-icon-btn:hover,
  :global(body.theme-cyber) .ui-icon-btn:hover {
    color: #f1f5f9;
    background: rgba(255, 255, 255, 0.08);
  }
</style>
