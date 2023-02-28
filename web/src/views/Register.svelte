<h1 class="text-3xl mb-6">Register your Knowledge Base</h1>

{#if alreadyRegistered}
  <div class="error">
    Currently, only one Knowledge Base can be registered.
    A Knowledge Base called <span class="quote">{registeredKb.name}</span> already exists.
  </div>
{:else}
  <form class="flex flex-col gap-5" on:submit|preventDefault={submit}>
    {#each Object.values(formItems) as item}
    <label class="block">
      <span>{item.label}</span>
      <input required bind:value={item.value} class="block w-full text-black" type="text" placeholder={item.label}>
    </label>
    {/each}
    <Button disabled={success} type="submit">Submit</Button>
  </form>
{/if}

<script lang="ts">
  import Button from "../lib/Button.svelte";
  import { register } from "../api";
  import { onMount } from "svelte";
  import { syncKnowledgeBases, knowledgeBases } from "../stores";

  // set to true for quicker testing
  let dev = false;

  let formItems = {
    id: {label: "ID", value: dev ? "http://example.org/kb1" : ""},
    name: {label: "Name", value: dev ? "KB1" : ""},
    description: {label: "Description", value: dev ? "Knowledge Base 1" : ""},
  }

  let alreadyRegistered;
  let registeredKb = undefined;

  onMount(async () => {
    await syncKnowledgeBases();
    if ($knowledgeBases.length > 0) {
      registeredKb = $knowledgeBases[0];
      alreadyRegistered = true;
    } else {
      alreadyRegistered = false;
    }
  })

  let success = false;

  async function submit() {
    try {
      await register(formItems.id.value, formItems.name.value, formItems.description.value);
      success = true;
      await syncKnowledgeBases();
      registeredKb = $knowledgeBases[0];
    } catch (e) {
      console.error(e);
    }
  }
</script>