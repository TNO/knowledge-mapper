<script>
  import "../app.css";
  let links = [
    {link: '/', title: 'Home'},
    {link: '/policies', title: 'Policies'},
    {link: '/access-attempts', title: 'Access attempts'},
  ]
</script>

<nav class="bg-emerald-200">
  <ul class="flex flex-row">
    {#each links as link}
      <li class="m-1 px-2 rounded bg-emerald-300 hover:bg-emerald-400">
        <a href="{link.link}">{link.title}</a>
      </li>
    {/each}
  </ul>
</nav>


<main>
  <slot/>
</main>