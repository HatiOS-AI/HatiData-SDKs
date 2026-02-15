# @hatidata/sdk

The official TypeScript SDK for [HatiData](https://hatidata.com) -- RAM for Agents. Connect to your HatiData instance from Node.js or browser environments with full type safety.

## Installation

```bash
npm install @hatidata/sdk
```

For local mode (in-process DuckDB, no server required):

```bash
npm install @hatidata/sdk @duckdb/duckdb-wasm
```

## Quick Start

### Connect and Query

```typescript
import { HatiDataClient } from "@hatidata/sdk";

const client = new HatiDataClient({
  host: "localhost",
  port: 8080,
  apiKey: "hd_your_api_key",
});

await client.connect();

// Execute SQL queries
const result = await client.query("SELECT * FROM sales LIMIT 10");
console.log(result.columns); // [{ name: "id", type: "INTEGER" }, ...]
console.log(result.rows);    // [{ id: 1, amount: 99.99 }, ...]
console.log(result.rowCount); // 10

// List tables
const tables = await client.listTables();
console.log(tables); // [{ name: "sales", schema: "main", columnCount: 5, rowCount: 1000 }]

await client.close();
```

### Local Mode (No Server)

Run queries entirely in-process using DuckDB-WASM -- perfect for development, testing, and edge workloads.

```typescript
import { LocalEngine } from "@hatidata/sdk";

const engine = new LocalEngine(); // or new LocalEngine(":memory:")
await engine.init();

await engine.query("CREATE TABLE events (id INT, name VARCHAR)");
await engine.query("INSERT INTO events VALUES (1, 'click'), (2, 'view')");

const result = await engine.query("SELECT * FROM events");
console.log(result.rows); // [{ id: 1, name: "click" }, { id: 2, name: "view" }]

await engine.close();
```

### Push & Pull Sync

Sync data between local and remote HatiData instances.

```typescript
import { HatiDataClient } from "@hatidata/sdk";

const client = new HatiDataClient({
  host: "localhost",
  port: 8080,
  apiKey: "hd_local_key",
});

await client.connect();

// Push local tables to cloud
const pushResult = await client.push({
  target: "cloud",
  tables: ["events", "users"],
  apiKey: "hd_cloud_key",
});
console.log(`Pushed ${pushResult.tablesSync} tables`);

// Pull remote tables locally
const pullResult = await client.pull({
  tables: ["analytics_summary"],
});
console.log(`Pulled ${pullResult.tablesPulled} tables`);

await client.close();
```

### Error Handling

```typescript
import {
  HatiDataClient,
  ConnectionError,
  QueryError,
  AuthenticationError,
} from "@hatidata/sdk";

const client = new HatiDataClient({ apiKey: "hd_my_key" });

try {
  await client.connect();
  const result = await client.query("SELECT * FROM nonexistent_table");
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error("Bad credentials:", error.message);
  } else if (error instanceof QueryError) {
    console.error("Query failed:", error.message, "SQLSTATE:", error.sqlState);
  } else if (error instanceof ConnectionError) {
    console.error("Connection issue:", error.message);
  }
} finally {
  await client.close();
}
```

## API Reference

### `HatiDataClient`

| Method | Description |
|--------|-------------|
| `constructor(config: HatiDataConfig)` | Create a new client instance |
| `connect(): Promise<void>` | Connect to the HatiData control plane |
| `query(sql, params?): Promise<QueryResult>` | Execute a SQL query |
| `listTables(): Promise<TableInfo[]>` | List all accessible tables |
| `push(options): Promise<{ tablesSync }>` | Push local data to cloud/VPC |
| `pull(options): Promise<{ tablesPulled }>` | Pull remote data locally |
| `close(): Promise<void>` | Close the connection |
| `state: ConnectionState` | Current connection state |

### `LocalEngine`

| Method | Description |
|--------|-------------|
| `constructor(dbPath?: string)` | Create engine (default: `.hati/local.duckdb`) |
| `init(): Promise<void>` | Initialize DuckDB-WASM |
| `query(sql): Promise<QueryResult>` | Execute a SQL query locally |
| `listTables(): Promise<TableInfo[]>` | List local tables |
| `close(): Promise<void>` | Close and release resources |

### Configuration

```typescript
interface HatiDataConfig {
  host?: string;      // Default: "localhost"
  port?: number;      // Default: 8080
  database?: string;  // Default: "default"
  user?: string;
  password?: string;
  apiKey?: string;     // Takes precedence over user/password
  ssl?: boolean;       // Default: false
  timeout?: number;    // Default: 30000 (ms)
}
```

### Error Types

| Error | Code | Description |
|-------|------|-------------|
| `HatiDataError` | varies | Base error class |
| `ConnectionError` | `CONNECTION_FAILED` | Connection issues |
| `QueryError` | `QUERY_ERROR` | Query execution failures (includes `sqlState`) |
| `AuthenticationError` | `AUTHENTICATION_FAILED` | Invalid credentials |
| `SyncError` | `SYNC_FAILED` | Push/pull sync failures |

## Tiers

| Tier | Connection | Use Case |
|------|-----------|----------|
| **Local** (free) | `LocalEngine` with DuckDB-WASM | Development, testing, edge |
| **Cloud** ($29/mo) | `HatiDataClient` to managed instance | Teams, production |
| **Enterprise** (VPC) | `HatiDataClient` to VPC-deployed instance | Regulated industries |

## Documentation

Full documentation is available at [docs.hatidata.com](https://docs.hatidata.com).

## License

Apache-2.0. Copyright Marviy Pte Ltd.
