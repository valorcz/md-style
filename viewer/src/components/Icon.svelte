<script lang="ts">
  export let name: string;
  export let size: number | string = 16;
  export let className: string = '';
  export let strokeWidth: number | string = 1.75;
  export let duotone: boolean = true;
  export let secondaryOpacity: number = 0.22;
</script>

<svg
  xmlns="http://www.w3.org/2000/svg"
  width={size}
  height={size}
  viewBox="0 0 24 24"
  fill="none"
  stroke="currentColor"
  stroke-width={strokeWidth}
  stroke-linecap="round"
  stroke-linejoin="round"
  class="modern-icon {className}"
  class:is-duotone={duotone}
  style="--icon-secondary-opacity: {secondaryOpacity};"
  aria-hidden="true"
>
  {#if name === 'search'}
    <circle cx="11" cy="11" r="8" class="duotone-bg"></circle>
    <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
  {:else if name === 'message-square'}
    <path class="duotone-bg" d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
  {:else if name === 'message-plus'}
    <path class="duotone-bg" d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
    <line x1="12" y1="7" x2="12" y2="13"></line>
    <line x1="9" y1="10" x2="15" y2="10"></line>
  {:else if name === 'layers'}
    <polygon points="12 2 2 7 12 12 22 7 12 2" class="duotone-bg"></polygon>
    <polyline points="2 17 12 22 22 17"></polyline>
    <polyline points="2 12 12 17 22 12"></polyline>
  {:else if name === 'box'}
    <path class="duotone-bg" d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"></path>
    <polyline points="3.27 6.96 12 12.01 20.73 6.96"></polyline>
    <line x1="12" y1="22.08" x2="12" y2="12"></line>
  {:else if name === 'check'}
    <polyline points="20 6 9 17 4 12"></polyline>
  {:else if name === 'check-circle'}
    <circle cx="12" cy="12" r="10" class="duotone-bg"></circle>
    <polyline points="16 9 10.5 14.5 8 12"></polyline>
  {:else if name === 'rotate-ccw'}
    <polyline points="1 4 1 10 7 10"></polyline>
    <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
  {:else if name === 'pencil' || name === 'edit'}
    <path class="duotone-bg" d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"></path>
    <path d="M12 20h9"></path>
  {:else if name === 'trash'}
    <path class="duotone-bg" d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"></path>
    <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
    <line x1="3" y1="6" x2="21" y2="6"></line>
    <line x1="10" y1="11" x2="10" y2="17"></line>
    <line x1="14" y1="11" x2="14" y2="17"></line>
  {:else if name === 'copy'}
    <rect x="9" y="9" width="13" height="13" rx="2" ry="2" class="duotone-bg"></rect>
    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
  {:else if name === 'code'}
    <polyline points="16 18 22 12 16 6"></polyline>
    <polyline points="8 6 2 12 8 18"></polyline>
  {:else if name === 'x'}
    <line x1="18" y1="6" x2="6" y2="18"></line>
    <line x1="6" y1="6" x2="18" y2="18"></line>
  {:else if name === 'sun'}
    <circle cx="12" cy="12" r="5" class="duotone-bg"></circle>
    <line x1="12" y1="1" x2="12" y2="3"></line>
    <line x1="12" y1="21" x2="12" y2="23"></line>
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
    <line x1="1" y1="12" x2="3" y2="12"></line>
    <line x1="21" y1="12" x2="23" y2="12"></line>
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
  {:else if name === 'moon'}
    <path class="duotone-bg" d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
  {:else if name === 'file-text'}
    <path class="duotone-bg" d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
    <polyline points="14 2 14 8 20 8"></polyline>
    <line x1="16" y1="13" x2="8" y2="13"></line>
    <line x1="16" y1="17" x2="8" y2="17"></line>
    <polyline points="10 9 9 9 8 9"></polyline>
  {:else if name === 'layout' || name === 'monitor'}
    <rect class="duotone-bg" x="2" y="3" width="20" height="14" rx="2" ry="2"></rect>
    <line x1="8" y1="21" x2="16" y2="21"></line>
    <line x1="12" y1="17" x2="12" y2="21"></line>
  {:else if name === 'printer'}
    <rect class="duotone-bg" x="6" y="14" width="12" height="8"></rect>
    <path class="duotone-bg" d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
    <polyline points="6 9 6 2 18 2 18 9"></polyline>
  {:else if name === 'academic'}
    <polygon class="duotone-bg" points="12 5 22 10 12 15 2 10 12 5"></polygon>
    <path d="M6 12v5c3 3 9 3 12 0v-5"></path>
    <path d="M22 10v6"></path>
  {:else if name === 'lightbulb'}
    <path class="duotone-bg" d="M15.09 14c.18-.98.65-1.74 1.41-2.5A4.65 4.65 0 0 0 18 8 6 6 0 0 0 6 8c0 1 .23 2.23 1.5 3.5.76.76 1.23 1.52 1.41 2.5h6.18z"></path>
    <line x1="9" y1="18" x2="15" y2="18"></line>
    <line x1="10" y1="22" x2="14" y2="22"></line>
  {:else if name === 'alert-circle'}
    <circle cx="12" cy="12" r="10" class="duotone-bg"></circle>
    <line x1="12" y1="8" x2="12" y2="12"></line>
    <line x1="12" y1="16" x2="12.01" y2="16"></line>
  {:else if name === 'help-circle'}
    <circle cx="12" cy="12" r="10" class="duotone-bg"></circle>
    <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
    <line x1="12" y1="17" x2="12.01" y2="17"></line>
  {:else if name === 'award' || name === 'thumbs-up'}
    <circle cx="12" cy="8" r="7" class="duotone-bg"></circle>
    <polyline points="8.21 13.89 7 23 12 20 17 23 15.79 13.88"></polyline>
  {:else if name === 'chevron-left'}
    <polyline points="15 18 9 12 15 6"></polyline>
  {:else if name === 'chevron-down'}
    <polyline points="6 9 12 15 18 9"></polyline>
  {:else if name === 'chevron-up'}
    <polyline points="18 15 12 9 6 15"></polyline>
  {:else if name === 'filter'}
    <polygon class="duotone-bg" points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
  {:else if name === 'target'}
    <circle cx="12" cy="12" r="10" class="duotone-bg"></circle>
    <circle cx="12" cy="12" r="6"></circle>
    <circle cx="12" cy="12" r="2"></circle>
  {:else if name === 'external-link'}
    <path class="duotone-bg" d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
    <polyline points="15 3 21 3 21 9"></polyline>
    <line x1="10" y1="14" x2="21" y2="3"></line>
  {:else if name === 'maximize' || name === 'zoom-in'}
    <path d="M15 3h6v6"></path>
    <path d="M9 21H3v-6"></path>
    <path d="M21 3l-7 7"></path>
    <path d="M3 21l7-7"></path>
  {:else if name === 'minimize' || name === 'zoom-out'}
    <path d="M4 14h6v6"></path>
    <path d="M20 10h-6V4"></path>
    <path d="M14 10l7-7"></path>
    <path d="M3 21l7-7"></path>
  {:else if name === 'download'}
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
    <polyline points="7 10 12 15 17 10"></polyline>
    <line x1="12" y1="15" x2="12" y2="3"></line>
  {:else if name === 'plus'}
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  {:else if name === 'minus'}
    <line x1="5" y1="12" x2="19" y2="12"></line>
  {:else if name === 'expand' || name === 'arrows-alt'}
    <polyline points="15 3 21 3 21 9"></polyline>
    <polyline points="9 21 3 21 3 15"></polyline>
    <polyline points="21 15 21 21 15 21"></polyline>
    <polyline points="3 9 3 3 9 3"></polyline>
  {:else}
    <circle cx="12" cy="12" r="10" class="duotone-bg"></circle>
  {/if}
</svg>

<style>
  .modern-icon {
    display: inline-block;
    vertical-align: middle;
    flex-shrink: 0;
  }

  /* Duotone Depth Layer */
  .modern-icon.is-duotone .duotone-bg {
    fill: var(--icon-secondary-fill, currentColor);
    fill-opacity: var(--icon-secondary-opacity, 0.22);
    transition: fill-opacity 0.2s ease, fill 0.2s ease;
  }

  /* Hover micro-interaction: subtle glow/tint deepen on interactive buttons */
  :global(button:hover) .modern-icon.is-duotone .duotone-bg,
  :global(.interactive-item:hover) .modern-icon.is-duotone .duotone-bg,
  :global(.btn:hover) .modern-icon.is-duotone .duotone-bg {
    fill-opacity: calc(var(--icon-secondary-opacity, 0.22) * 1.5);
  }

  /* Pure strokes stay clear of unwanted fills */
  .modern-icon line,
  .modern-icon polyline {
    fill: none !important;
  }
</style>
