<script lang="ts">
	import { createEventDispatcher } from "svelte";

  export let fields: {[key: string]: { type: "text" | "date" | "select" | "textarea" | "JsonFile", label: string, placeholder?: string, options?: {value: string, label: string, disabled?: boolean}[]}}

  export let submitLabel = "Save";

  let form;

  const dispatch = createEventDispatcher();

  async function onSubmit(e: SubmitEvent) {
    const formData = new FormData(e.target as HTMLFormElement);

    const data: {[key: string]: any} = {};
    for (let field of formData) {
      const [key, value] = field;
      if (fields[key].type == "JsonFile") {
        const el = form.querySelector(`input[name=${key}]`);
        const fileText = await el.files[0].text();
        data[key] = JSON.parse(fileText);
      } else {
        data[key] = value;
      }
    }
    dispatch('submit', data);
  }
</script>

<form bind:this={form} class="flex flex-col gap-4" on:submit|preventDefault={onSubmit}>
  {#each Object.entries(fields) as [name, {type, label, placeholder, options}]}
    <div class="flex flex-row justify-between items-center gap-4">
      <label class="w-1/2" for="{name}">{label}</label>
      {#if type == "select"}
        <select name="{name}">
          {#each options as {value, label, disabled}}
            <option value="{value}" disabled={disabled}>{label}</option>
          {/each}
        </select>
      {:else if type == "textarea"}
        <textarea name="{name}" cols="30" rows="6"></textarea>
      {:else if type == "JsonFile"}
        <input name="{name}" type="file" accept="application/json" />
      {:else}
        <input name="{name}" class="w-1/2" type="{type}" placeholder="{placeholder}">
      {/if}
    </div>
  {/each}
  <button type="submit">{submitLabel}</button>
</form>
