import { exec } from "$lib/db";

export async function get() {
  type RowType = { count: bigint, knowledge_base_id: string, knowledge_interaction_id: string, last_attempt: Date };
  // For each KB/KI combo that we do not have policies on, get the number of
  // attempts and the last attempt time.
  const rows: RowType[] = await exec(`
    SELECT
      COUNT(id) AS count, knowledge_base_id, knowledge_interaction_id, MAX(access_datetime) AS last_attempt
      FROM access_log
      WHERE NOT EXISTS (
        SELECT 1
        FROM policies
        WHERE
          policies.knowledge_interaction_id = access_log.knowledge_interaction_id
          AND
          policies.knowledge_base_id = access_log.knowledge_base_id
      )
      GROUP BY knowledge_interaction_id, knowledge_base_id
    ;`
  );
  return {
    body: rows
      .map(row => ({... row, count: Number(row.count)})) // convert bigints to numbers
  }
}
