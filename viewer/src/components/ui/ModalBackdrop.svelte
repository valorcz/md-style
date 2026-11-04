<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let isOpen: boolean = true;
  export let blur: boolean = true;
  export let zIndex: number = 9997;
  export let top: string = '0';

  let clazz: string = '';
  export { clazz as class };

  const dispatch = createEventDispatcher<{
    click: MouseEvent;
    close: void;
  }>();

  function handleClick(e: MouseEvent) {
    dispatch('click', e);
    dispatch('close');
  }
</script>

{#if isOpen}
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div
    class="ui-modal-backdrop {clazz}"
    class:has-blur={blur}
    style="z-index: {zIndex}; top: {top};"
    on:click={handleClick}
  >
    <slot />
  </div>
{/if}

<style>
  .ui-modal-backdrop {
    position: fixed;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.25);
    user-select: none;
    transition: opacity 0.2s ease;
  }

  .ui-modal-backdrop.has-blur {
    backdrop-filter: blur(4px);
    -webkit-backdrop-filter: blur(4px);
  }

  :global([data-theme="dark"]) .ui-modal-backdrop,
  :global(body.theme-cyber) .ui-modal-backdrop,
  :global(body.dark-theme) .ui-modal-backdrop {
    background: rgba(0, 0, 0, 0.55);
  }
</style>
