<!--
Example graph pattern:
?a <http://example.org/predicate-1> ?b .
-->

<script lang="ts">
    import Form from "../lib/Form.svelte";

    function numberOfGraphPatternsForDataSourceType(dataSourceType: "JsonData") {
      if (dataSourceType == "JsonData") {
        return 1;
      } else {
        throw new Error(`Invalid data source type ${dataSourceType}`);
      }
    }

    let step = 1;

    let step1Values = {
      name: undefined,
      type: undefined,
    };
    $: step1Fields = {
      "name": {type: "text" as const, label: "Name:", value: step1Values.name},
      "type": {
        type: "select" as const,
        label: "Type:",
        options: [
          {value: "JsonData", label: "Static JSON data"},
        ],
        value: step1Values.type,
      },
    };
   function onStep1Submit({ detail }) {
      Object.keys(step1Fields).forEach(k => {
        step1Values[k] = detail[k];
      });
      // TODO: Name validation
      step1Values = step1Values;
      step = 2;
    }

    let step2Values = {
      graphPattern1: undefined,
      graphPattern2: undefined,
    };
    function step2Fields() {
      let nPatterns = numberOfGraphPatternsForDataSourceType(step1Values.type);
      if (nPatterns == 1) {
        return {
          "graphPattern1": {type: "textarea" as const, label: "Graph pattern:"},
        }
      } else {
        return {
          "graphPattern1": {type: "textarea" as const, label: "Argument graph pattern:"},
          "graphPattern2": {type: "textarea" as const, label: "Result graph pattern:"},
        }
      }
    };

    function onStep2Submit({ detail }) {
      console.log(detail);
      Object.keys(step2Values).forEach(k => {
        step2Values[k] = detail[k];
      });
      step2Values = step2Values;
      step = 3;
    }

    let step3Values = {
      bindings: undefined,
    };
    function step3Fields() {
      if (step1Values.type == "JsonData") {
        return {
          "bindings": {type: "JsonFile" as const, label: "JSON file"}
        }
      } else {
        throw new Error("Data source types other than 'JsonData' are not supported yet.");
      }
    }
    function onStep3Submit({ detail }) {
      Object.keys(step3Values).forEach(k => {
        step3Values[k] = detail[k];
      });
      if (step3Values.bindings != undefined) {
        // TODO: Validate that it is an array, and that all bindings use all
        // variables.
      }
      step3Values = step3Values;

      const sendToApi = {
        name: step1Values.name,
        type: step1Values.type,
        graphPattern1: step2Values.graphPattern1,
        graphPattern2: step2Values.graphPattern2,
        bindings: step3Values.bindings,
      };
      console.log(sendToApi);
    }
</script>

<h1 class="text-3xl mb-6">Register your data source</h1>

{#if step == 1}
  <Form fields={step1Fields} submitLabel="Next" on:submit={onStep1Submit}></Form>
{:else if step == 2}
  <Form fields={step2Fields()} submitLabel="Next" on:submit={onStep2Submit}></Form>
{:else if step == 3}
  <Form fields={step3Fields()} submitLabel="Submit" on:submit={onStep3Submit}></Form>
{/if}
