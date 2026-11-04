<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import Icon from '../Icon.svelte';

  export let options: { id: string; label: string; icon?: string; title?: string }[] = [];
  export let value: string = '';
  export let size: 'sm' | 'md' = 'sm';
  export let itemClass: string = '';

  let clazz: string = '';
  export { clazz as class };

  const dispatch = createEventDispatcher<{
    change: string;
  }>();

  function selectOption(id: string) {
    if (value === id) return;
    value = id;
    dispatch('change', id);
  }
</script>

<div class="ui-segmented-control size-{size} {clazz}" role="group" aria-label="Segmented Control">
  {#each options as opt}
    <button
      type="button"
      class="segment-item {itemClass}"
      class:is-active={value === opt.id}
      title={opt.title || opt.label}
      aria-pressed={value === opt.id}
      on:click={() => selectOption(opt.id)}
    >
      {#if opt.icon}
        <Icon name={opt.icon} size={size === 'sm' ? 12 : 14} />
      {/if}
      <span class="segment-label">{opt.label}</span>
    </button>
  {/each}
</div>

<style>
  .ui-segmented-control {
    display: inline-flex;
    align-items: center;
    background: rgba(0, 0, 0, 0.06);
    border: 1px solid var(--color-border, rgba(0, 0, 0, 0.08));
    border-radius: 6px;
    padding: 2px;
    gap: 2px;
    user-select: none;
    box-sizing: border-box;
  }

  .segment-item {
    appearance: none;
    -webkit-appearance: none;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.35rem;
    background: transparent;
    border: none;
    outline: none;
    box-shadow: none;
    color: var(--color-text-muted, #64748b);
    padding: 0.18rem 0.55rem;
    margin: 0;
    border-radius: 4px;
    font-size: 0.72rem;
    font-weight: 500;
    font-family: inherit;
    cursor: pointer;
    transition: background 0.14s ease, color 0.14s ease, box-shadow 0.14s ease;
    white-space: nowrap;
  }

  .ui-segmented-control.size-md .segment-item {
    padding: 0.28rem 0.75rem;
    font-size: 0.78rem;
  }

  .segment-item:hover {
    color: var(--color-text, #0f172a);
  }

  .segment-item.is-active {
    background: var(--color-paper, #ffffff);
    color: var(--color-text, #0f172a);
    font-weight: 600;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  }

  .segment-item:focus-visible {
    outline: 2px solid var(--color-accent, #0284c7);
    outline-offset: 1px;
  }

  /* Dark Theme Support */
  :global([data-theme="dark"]) .ui-segmented-control,
  :global(body.theme-cyber) .ui-segmented-control,
  :global(body.dark-theme) .ui-segmented-control {
    background: rgba(0, 0, 0, 0.35);
    border-color: rgba(255, 255, 255, 0.1);
  }

  :global([data-theme="dark"]) .segment-item,
  :global(body.theme-cyber) .segment-item,
  :global(body.dark-theme) .segment-item {
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .segment-item:hover,
  :global(body.theme-cyber) .segment-item:hover,
  :global(body.dark-theme) .segment-item:hover {
    color: #f8fafc;
  }

  :global([data-theme="dark"]) .segment-item.is-active,
  :global(body.theme-cyber) .segment-item.is-active,
  :global(body.dark-theme) .segment-item.is-active {
    background: rgba(255, 255, 255, 0.15);
    color: #ffffff;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.3);
  }
</style>
