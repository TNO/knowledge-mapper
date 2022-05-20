<svelte:head>
  <title>KM | Access Attempts </title>
</svelte:head>

<script lang="ts">
   export let attempts: any;
</script>

<h1>Access attempts</h1>

<table>
  <thead></thead>
  <tbody>
    {#each attempts as attempt}
      <tr>
        <td>{attempt.knowledge_base_id}</td>
        <td>{attempt.knowledge_interaction_id}</td>
        <td>{attempt.last_attempt}</td>
      </tr>
    {/each}
  </tbody>
</table>
