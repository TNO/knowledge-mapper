import { get, writable } from "svelte/store";

const DEFAULT_KM_API_URL = '/km/';
export const knowledgeMapperApiUrl = writable(localStorage.knowledgeMapperApiUrl || DEFAULT_KM_API_URL);

export const resetKnowledgeMapperApiUrl = () => {
  knowledgeMapperApiUrl.set(DEFAULT_KM_API_URL);
}
knowledgeMapperApiUrl.subscribe((value) => localStorage.knowledgeMapperApiUrl = value);

export const connectionErrors = writable([]);

const addConnectionError = (err) => {
  connectionErrors.update(es => {
    es.push(err);
    return es;
  });
}

export const knowledgeBases = writable(undefined);

export const syncKnowledgeBases = async () => {
  connectionErrors.set([]);

  let resp;
  const url = `${get(knowledgeMapperApiUrl)}knowledge-bases/`
  try {
    resp = await fetch(url);
    resp.status
  } catch (e) {
    const errMessage = `Could not connect to ${url}`;
    addConnectionError({message: errMessage});
    throw new Error(errMessage);
  }

  if (!resp.ok) {
    addConnectionError({response: resp});
    throw new Error('Knowledge Mapper API request returned unsuccesfully');
  }
  knowledgeBases.set((await resp.json()).data);
}
