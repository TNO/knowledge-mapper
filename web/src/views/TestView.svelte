<script lang="ts">
  import Form from "../lib/Form.svelte";


  const fields = {
    "aFile": {type: "JsonFile" as const, label: "JSON file"}
  }

  let output = {};
  function onSubmit({detail}) {
    output = detail;
  }
</script>

 <h1>Test view</h1>

 <Form fields={fields} on:submit={onSubmit}></Form>

 <p>{JSON.stringify(output)}</p>