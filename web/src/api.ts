import { get } from "svelte/store";
import { knowledgeMapperApiUrl } from "./stores";

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