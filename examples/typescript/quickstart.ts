/**
 * HatiData TypeScript SDK — Quickstart
 *
 * Prerequisites:
 *   npm install @hatidata/sdk
 *
 * Usage:
 *   npx tsx quickstart.ts
 */

import { HatiDataClient } from "@hatidata/sdk";

async function main() {
  // Connect to local HatiData instance
  const client = new HatiDataClient({
    host: "localhost",
    port: 5439,
    database: "main",
  });

  await client.connect();
  console.log("Connected to HatiData");

  // Create a table using Snowflake-compatible SQL
  await client.query(
    "CREATE TABLE IF NOT EXISTS events (id INT, name VARCHAR, created_at TIMESTAMP)"
  );

  // Insert data
  await client.query(
    "INSERT INTO events VALUES (1, 'signup', CURRENT_TIMESTAMP)"
  );

  // Query with Snowflake functions — transpiled automatically
  const result = await client.query(
    "SELECT id, name, NVL(name, 'unknown') as safe_name FROM events"
  );

  console.log(`\nQuery returned ${result.rowCount} rows:`);
  for (const row of result.rows) {
    console.log(" ", row);
  }

  // List tables
  const tables = await client.listTables();
  console.log("\nTables:", tables.map((t) => t.name));

  await client.close();
  console.log("\nDone!");
}

main().catch(console.error);
