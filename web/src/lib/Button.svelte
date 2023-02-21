
<button
  type={type}
  on:click
  disabled={disabled}
  class="rounded p-1"
  class:bg-slate-300={disabled}
  class:bg-slate-500={!disabled}
>
  <slot/>
</button>

<script lang="ts">
  export let disabled = false;
  export let type = "button" as const;
</script>