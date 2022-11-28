<script>
  import { connectionErrors, resetKnowledgeMapperApiUrl, knowledgeMapperApiUrl, syncKnowledgeBases } from "../stores.js";
  import Button from "../lib/Button.svelte";

  function onClickReset() {
    resetKnowledgeMapperApiUrl();
    syncKnowledgeBases();
  }
</script>

<h1 class="text-3xl">Connect</h1>

<div>
  Using Knowledge Mapper endpoint: <span class="quote">{$knowledgeMapperApiUrl}</span>
  <Button on:click={onClickReset}>
    Reset <span class="material-icons">lock_reset</span>
  </Button>
</div>


{#if $connectionErrors.length > 0}
  <ul class="text-red-400 mt-2">
    {#each $connectionErrors as err}
      <li>
        <span class="relative inline-block">
          <span class="inline-flex items-center justify-center px-2 py-1 mr-1 text-xs font-bold leading-none text-red-100 bg-red-600 rounded-full">ERROR</span>
        </span>
        {#if err.response != undefined}
          While requesting <span class="p-1 font-mono bg-black">{err.response.url}</span>
          received <span class="p-1 font-mono bg-black">{err.response.status} {err.response.statusText}</span>.
        {/if}
      </li>
    {/each}
  </ul>
{/if}