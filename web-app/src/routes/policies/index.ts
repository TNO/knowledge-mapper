import { exec } from "$lib/db";
import type { RequestHandler } from "@sveltejs/kit";

export async function get() {
  type RowType = { id: number, knowledge_base_id?: string, knowledge_interaction_id?: string };
  // For each KB/KI combo that we do not have policies on, get the number of
  // attempts and the last attempt time.
  const rows: RowType[] = await exec(`
    SELECT
      id,
      knowledge_base_id,
      knowledge_interaction_id
    FROM
      policies
    ;`
  );
  return {
    body: {
      policies: rows
    }
  }
}

export const post: RequestHandler = async (ev) => {
  const formData = await ev.request.formData();
  const knowledge_base_id = formData.get('knowledge_base_id');
  const knowledge_interaction_id = formData.get('knowledge_interaction_id');
  await exec(`
    INSERT INTO policies
      (knowledge_base_id, knowledge_interaction_id)
    VALUES
      (?, ?)
    ;`,
    [knowledge_base_id, knowledge_interaction_id]
  );
  return {
    status: 201,
  }
}