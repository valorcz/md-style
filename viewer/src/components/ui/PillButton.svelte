<script lang="ts">
  export let active: boolean = false;
  export let title: string = '';
  let clazz: string = '';
  export { clazz as class };
</script>

<button
  type="button"
  class="ui-pill-btn {clazz}"
  class:is-active={active}
  {title}
  on:click
>
  <slot />
</button>

<style>
  .ui-pill-btn {
    appearance: none;
    -webkit-appearance: none;
    background: rgba(0, 0, 0, 0.04);
    border: 1px solid var(--color-border, rgba(0, 0, 0, 0.08));
    color: var(--color-text-muted, #475569);
    padding: 0.12rem 0.45rem;
    margin: 0;
    border-radius: 4px;
    font-size: 0.7rem;
    font-family: inherit;
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    transition: all 0.15s ease;
  }

  .ui-pill-btn:hover {
    color: #0f172a;
    border-color: rgba(0, 0, 0, 0.2);
  }

  .ui-pill-btn.is-active {
    background: rgba(2, 132, 199, 0.1);
    border-color: #0284c7;
    color: #0284c7;
    font-weight: 600;
  }

  :global([data-theme="dark"]) .ui-pill-btn,
  :global(body.theme-cyber) .ui-pill-btn {
    background: transparent;
    border-color: rgba(255, 255, 255, 0.1);
    color: #94a3b8;
  }

  :global([data-theme="dark"]) .ui-pill-btn:hover,
  :global(body.theme-cyber) .ui-pill-btn:hover {
    color: #f1f5f9;
    border-color: rgba(255, 255, 255, 0.25);
  }

  :global([data-theme="dark"]) .ui-pill-btn.is-active,
  :global(body.theme-cyber) .ui-pill-btn.is-active {
    background: rgba(56, 189, 248, 0.15);
    border-color: #38bdf8;
    color: #38bdf8;
  }
</style>
