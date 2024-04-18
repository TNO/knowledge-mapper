<svelte:head>
  <title>KM | Access Attempts </title>
</svelte:head>

<script lang="ts">
   export let attempts: any;

   function formatDate(date: string | Date) {
     date = new Date(date);
     return `${date.getFullYear()}-${(date.getMonth() + 1).toString().padStart(2, '0')}-${date.getDate().toString().padStart(2, '0')} ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
   }
</script>

<h1 class="m-4 text-3xl font-bold underline">Access attempts</h1>

<p class="m-4">
  This page shows access attempts from Knowledge Bases to your Knowledge Interactions.
  It does not show access attempts that currently pass a policy.
</p>

<table class="mx-auto table-auto border-2 border-slate-500">
  <thead>
    <tr class="text-lg">
      <th>Knowledge Base</th>
      <th></th>
      <th>Knowledge Interaction</th>
      <th>Count</th>
      <th>Last attempt</th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    {#each attempts as attempt}
      <tr class="odd:bg-emerald-100">
        <td class="p-2 italic">{attempt.knowledge_base_id}</td>
        <td class="p-2">tried to access</td>
        <td class="p-2 italic">{attempt.knowledge_interaction_id}</td>
        <td class="p-2">{attempt.count}</td>
        <td class="p-2">{formatDate(attempt.last_attempt)}</td>
        <td class="p-2">
          <form action="/policies" method="post">
            <input type="hidden" name="knowledge_base_id" value={attempt.knowledge_base_id}>
            <input type="hidden" name="knowledge_interaction_id" value={attempt.knowledge_interaction_id}>
            <button type="submit" class="bg-green-200 border-2 border-green-400 hover:border-green-600 hover:bg-green-500 hover:text-white rounded-lg">Give access</button>
          </form>
        </td>
      </tr>
    {/each}
  </tbody>
</table>
