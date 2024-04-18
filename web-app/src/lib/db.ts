import * as mariadb from "mariadb";
import 'dotenv/config';

const pool = mariadb.createPool({
  host: process.env['DB_HOST'],
  port: parseInt(process.env['DB_PORT'] as string, 10),
  user: process.env['DB_USER'],
  password: process.env['DB_PASSWORD'],
  database: process.env['DB_DATABASE'],
  timezone: 'UTC',
});

export const exec = async (query: string, bindings?: unknown[]) => {
  let conn;
  let res;
  try {
    conn = await pool.getConnection();
    res = await conn.query(query, bindings);
    await conn.end()
  } finally {
    if (conn) {
      conn.release();
    } 
  }
  return res;
}
