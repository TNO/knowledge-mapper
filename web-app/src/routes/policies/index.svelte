<svelte:head>
  <title>KM | Policies </title>
</svelte:head>

<script lang="ts">
   export let policies: any;
</script>

<h1 class="m-4 text-3xl font-bold underline">Policies</h1>

<p class="m-4">
  This page shows the policies for the Knowledge Interactions inside this Knowledge Mapper.
</p>

{#if policies.length > 0}
  <table class="mx-auto table-auto border-2 border-slate-500">
    <thead>
      <tr class="text-lg">
        <th>Knowledge Base</th>
        <th></th>
        <th>Knowledge Interaction</th>
      </tr>
    </thead>
    <tbody>
      {#each policies as policy}
        <tr class="odd:bg-emerald-100">
          {#if policy.knowledge_base_id}
            <td class="italic p-2">{policy.knowledge_base_id}</td>
          {:else}
            <td class="italic font-black p-2">all knowledge bases</td>
          {/if}
          <td>can access</td>
          {#if policy.knowledge_interaction_id}
            <td class="italic p-2">{policy.knowledge_interaction_id}</td>
          {:else}
            <td class="italic font-black p-2">all knowledge interactions</td>
          {/if}
        </tr>
      {/each}
    </tbody>
  </table>
{:else}
  <p class="text-center italic m-auto">
    If there were policies, they would show up here!

    Take a look at the <a class="underline hover:bg-emerald-100" href="/access-attempts">access attempts</a> to see if any Knowledge Bases try to use your data.
  </p>
{/if}
