<script>
  import { Router, Link, Route, link } from "svelte-navigator";
  import Register from "./views/Register.svelte";
  import Connect from "./views/Connect.svelte";
  import { connectionErrors, knowledgeBases, syncKnowledgeBases } from "./stores";
  import { onMount } from "svelte";
    import { subscribe } from "svelte/internal";

  let navLinks = [
    {to: "/", text: "Home", icon: "home"},
    {to: "/connect", text: "Connect", icon: "electrical_services"},
    {to: "/register", text: "Register", icon: "category", icon2: "add"},
    {to: "/register-knowledge-interaction", text: "Register Knowledge Interaction", icon: "compare_arrows", icon2: "add"},
  ]

  subscribe(connectionErrors, (ce) => {
    if (ce.length > 0) {
      navLinks[1].badge = true;
    } else {
      navLinks[1].badge = false;
    }
  })

  onMount(async () => {
    await syncKnowledgeBases();
  })

</script>

<main class="flex flex-row gap-2 h-screen w-screen bg-slate-700 text-gray-200">
  <Router>
    <nav class="flex flex-col gap-1 items-center shrink mr-2 bg-slate-800">
      {#each navLinks as link}
        <Link class="p-2 hover:bg-slate-900" to={link.to}>
          <span class="relative inline-block">
            <span class="material-icons">{link.icon}</span>{#if link.icon2 != undefined }<span class="m-0 material-icons">{link.icon2}</span>{/if}
            {#if link.badge}
              <span class="absolute top-0 right-0 inline-flex items-center justify-center px-2 py-1 text-xs font-bold leading-none text-red-100 transform translate-x-1/2 -translate-y-1/2 bg-red-600 rounded-full">!</span>
            {/if}
          </span>
        </Link>
      {/each}
    </nav>
    <div>
      <Route path="/">
        <h1>Welcome</h1>
      </Route>
      <Route path="/register">
        <Register></Register>
      </Route>
      <Route path="/connect">
        <Connect></Connect>
      </Route>
    </div>
  </Router>
</main>
