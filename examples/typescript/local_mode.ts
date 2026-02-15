/**
 * HatiData Local Mode — DuckDB-WASM
 *
 * Run queries entirely in the browser/Node.js using DuckDB-WASM.
 * No server required.
 *
 * Prerequisites:
 *   npm install @hatidata/sdk @duckdb/duckdb-wasm
 *
 * Usage:
 *   npx tsx local_mode.ts
 */

import { LocalEngine } from "@hatidata/sdk";

async function main() {
  console.log("Initializing local DuckDB-WASM engine...");

  const engine = new LocalEngine();
  await engine.init();

  // Create table and insert data — no network required
  await engine.execute(
    "CREATE TABLE products (id INT, name VARCHAR, price DECIMAL(10,2))"
  );
  await engine.execute(
    "INSERT INTO products VALUES (1, 'Widget', 9.99), (2, 'Gadget', 24.99), (3, 'Doohickey', 4.99)"
  );

  // Query locally
  const result = await engine.query("SELECT * FROM products ORDER BY price DESC");
  console.log("\nProducts (sorted by price):");
  for (const row of result.rows) {
    console.log(`  ${row.name}: $${row.price}`);
  }

  // Aggregation
  const stats = await engine.query(
    "SELECT COUNT(*) as count, SUM(price) as total, AVG(price) as avg_price FROM products"
  );
  console.log("\nStats:", stats.rows[0]);

  await engine.close();
  console.log("\nDone! All queries ran locally — no server needed.");
}

main().catch(console.error);
