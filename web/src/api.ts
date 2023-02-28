import { get } from "svelte/store";
import { knowledgeMapperApiUrl, knowledgeBases } from "./stores";

export async function register(id, name, description) {
  const resp = await fetch(
    `${get(knowledgeMapperApiUrl)}knowledge-bases/`,
    {
      method: 'POST',
      body: JSON.stringify({
        id_url: id,
        name: name,
        description: description,
      }),
      headers: {
        'Content-Type': 'application/json'
      },
    });
  if (!resp.ok) {
    throw new Error("That didn't work.");
  }
}

export async function registerDataSource(details) {
  console.log(get(knowledgeBases)); 
  const kbId = get(knowledgeBases)[0].id;
  const resp = await fetch(
    `${get(knowledgeMapperApiUrl)}knowledge-bases/${kbId}/data-sources/`,
    {
      method: 'POST',
      body: JSON.stringify(details),
      headers: {
        'Content-Type': 'application/json'
      },
    }
  );
  if (!resp.ok) {
    throw new Error("That didn't work.");
  }
  return await resp.json();
}