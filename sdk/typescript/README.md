# @hatidata/sdk

[![npm version](https://img.shields.io/npm/v/@hatidata/sdk.svg)](https://www.npmjs.com/package/@hatidata/sdk)
[![License](https://img.shields.io/npm/l/@hatidata/sdk.svg)](https://github.com/HatiOS-AI/HatiData-SDKs/blob/main/LICENSE)

**Every Agent Deserves a Brain.** TypeScript SDK for [HatiData](https://hatidata.com) -- the agent-native data platform. Sub-10ms SQL queries, plus a full Control Plane client for agent memory, semantic triggers, state branching, chain-of-thought audit trails, and JIT access.

## Installation

```bash
npm install @hatidata/sdk
```

## Three Clients, One SDK

| Client | Purpose | Protocol |
|--------|---------|----------|
| `HatiDataClient` | SQL queries via control plane | REST API |
| `ControlPlaneClient` | Agent-native features (memory, triggers, branches, CoT) | REST API |
| `LocalEngine` | In-process DuckDB-WASM queries | Local |

## Quick Start -- SQL Queries

```typescript
import { HatiDataClient } from "@hatidata/sdk";

const client = new HatiDataClient({
  host: "localhost",
  port: 8080,
  apiKey: "hd_your_api_key",
});

await client.connect();
const result = await client.query("SELECT * FROM sales LIMIT 10");
console.log(result.rows);
await client.close();
```

## Quick Start -- Control Plane

```typescript
import { ControlPlaneClient } from "@hatidata/sdk";

const cp = new ControlPlaneClient({
  baseUrl: "https://api.hatidata.com",
  email: "you@company.com",
  password: "...",
});
await cp.login();

// Agent memory
await cp.createMemory({ agentId: "my-agent", content: "User prefers dark mode" });
const results = await cp.searchMemory({ query: "user preferences", topK: 5 });

// Semantic triggers
const trigger = await cp.createTrigger({ name: "PII detected", concept: "personal data exposure" });
const test = await cp.testTrigger(trigger.id, "User SSN is 123-45-6789");

// State branching
const branch = await cp.createBranch({ agentId: "analyst", tables: ["portfolio"] });
await cp.mergeBranch(branch.id, "branch_wins");

// Chain-of-thought audit trail
const [sessionId, traces] = ControlPlaneClient.buildCotSession({
  agentId: "my-agent",
  orgId: cp.orgId,
  steps: [
    { type: "Thought", content: { text: "Analyzing customer data" } },
    { type: "ToolCall", content: { tool: "sql_query", query: "SELECT ..." } },
    { type: "LlmResponse", content: { answer: "Found 42 enterprise accounts" } },
  ],
});
await cp.ingestCot(traces);
const verification = await cp.verifyCot(sessionId); // SHA-256 hash chain
```

## Features

### Data Plane (`HatiDataClient`)

- **Sub-10ms query latency** -- in-VPC execution, no data leaves your network
- **Push & pull sync** -- sync data between local and remote instances
- **Full type safety** -- all responses are fully typed
- **Snowflake SQL compatible** -- bring existing queries without rewrites

### Control Plane (`ControlPlaneClient`)

- **Agent memory** -- store, search, and manage long-term agent memories with vector embeddings
- **Semantic triggers** -- register concept-based triggers that fire on semantic similarity
- **State branching** -- create isolated data branches for experimentation, merge winners, discard losers
- **Chain-of-thought** -- SHA-256 hash-chained audit trails for tamper-evident reasoning logs
- **JIT access** -- request time-bounded privilege escalation for agents and humans
- **JWT and API key auth** -- auto-login on first request, org-scoped endpoints

### Local Mode (`LocalEngine`)

- **Zero server dependency** -- run queries entirely in-process using DuckDB-WASM
- **Development & testing** -- perfect for unit tests and local development
- **Edge workloads** -- deploy with your agent, no network required

## Control Plane API Reference

### Authentication

```typescript
// JWT auth (auto-login on first request)
const cp = new ControlPlaneClient({ baseUrl: "...", email: "...", password: "..." });
await cp.login();

// API key auth (no login needed)
const cp = new ControlPlaneClient({ baseUrl: "...", apiKey: "hd_live_...", orgId: "org-..." });
```

### Agent Memory

```typescript
// Create
const mem = await cp.createMemory({ agentId: "agent-1", content: "...", memoryType: "observation" });

// List with filters
const memories = await cp.listMemories({ agentId: "agent-1", memoryType: "observation", limit: 20 });

// Semantic search
const results = await cp.searchMemory({ query: "user preferences", agentId: "agent-1", topK: 5 });

// Delete
await cp.deleteMemory(mem.id);

// Embedding stats
const stats = await cp.embeddingStats();
```

### Semantic Triggers

```typescript
const trigger = await cp.createTrigger({
  name: "PII Detected",
  concept: "personal data exposure",
  threshold: 0.85,
  actions: ["webhook"],
  cooldownSecs: 60,
});

const triggers = await cp.listTriggers();
const result = await cp.testTrigger(trigger.id, "Customer SSN is 123-45-6789");
await cp.deleteTrigger(trigger.id);
```

### State Branching

```typescript
const branch = await cp.createBranch({
  agentId: "analyst",
  tables: ["portfolio"],
  description: "Conservative rebalance",
});

const branches = await cp.listBranches();
const diff = await cp.branchDiff(branch.id);
const conflicts = await cp.branchConflicts(branch.id);
const cost = await cp.branchCost(branch.id);
const analytics = await cp.branchAnalytics();

await cp.mergeBranch(branch.id, "branch_wins");
await cp.discardBranch(otherBranchId);
```

### Chain-of-Thought

```typescript
// Build hash-chained session
const [sessionId, traces] = ControlPlaneClient.buildCotSession({
  agentId: "my-agent",
  orgId: "org-...",
  steps: [
    { type: "Thought", content: { text: "..." } },
    { type: "ToolCall", content: { tool: "search", query: "..." } },
    { type: "ToolResult", content: { count: 42 } },
    { type: "LlmResponse", content: { answer: "..." } },
  ],
});

await cp.ingestCot(traces);
const verification = await cp.verifyCot(sessionId);
const replay = await cp.replayCot(sessionId);
const sessions = await cp.listCotSessions();
```

### JIT Access

```typescript
const grant = await cp.requestJit({ targetRole: "admin", reason: "deploy fix", durationHours: 2 });
const grants = await cp.listJitGrants();
```

## Local Mode

```typescript
import { LocalEngine } from "@hatidata/sdk";

const engine = new LocalEngine(":memory:");
await engine.init();

await engine.query("CREATE TABLE events (id INT, name VARCHAR)");
await engine.query("INSERT INTO events VALUES (1, 'click'), (2, 'view')");
const result = await engine.query("SELECT * FROM events");

await engine.close();
```

Requires `@duckdb/duckdb-wasm` as a peer dependency: `npm install @duckdb/duckdb-wasm`

## Error Handling

```typescript
import { ControlPlaneClient, AuthenticationError, ConnectionError, HatiDataError } from "@hatidata/sdk";

try {
  await cp.createMemory({ agentId: "agent-1", content: "test" });
} catch (error) {
  if (error instanceof AuthenticationError) {
    console.error("Bad credentials:", error.message);
  } else if (error instanceof ConnectionError) {
    console.error("Connection issue:", error.message);
  } else if (error instanceof HatiDataError) {
    console.error("API error:", error.message, error.code);
  }
}
```

## Documentation

- [Getting Started](https://docs.hatidata.com/getting-started)
- [TypeScript SDK Reference](https://docs.hatidata.com/sdks/typescript)
- [Control Plane API](https://docs.hatidata.com/api-reference)
- [Agent Memory](https://docs.hatidata.com/features/agent-memory)
- [Semantic Triggers](https://docs.hatidata.com/features/semantic-triggers)
- [State Branching](https://docs.hatidata.com/features/branching)
- [Chain-of-Thought](https://docs.hatidata.com/features/chain-of-thought)

## License

Apache-2.0. Copyright Marviy Pte Ltd.
