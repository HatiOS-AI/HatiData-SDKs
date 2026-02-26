/**
 * Configuration for connecting to a HatiData instance.
 */
export interface HatiDataConfig {
  /** Hostname of the HatiData proxy or control plane. Defaults to "localhost". */
  host?: string;

  /** Port number. Defaults to 8080 (control plane HTTP API). */
  port?: number;

  /** Database name. Defaults to "default". */
  database?: string;

  /** Username for authentication. */
  user?: string;

  /** Password for authentication. */
  password?: string;

  /** API key for control plane authentication. Takes precedence over user/password. */
  apiKey?: string;

  /** Enable TLS/SSL for the connection. Defaults to false. */
  ssl?: boolean;

  /** Query timeout in milliseconds. Defaults to 30000 (30 seconds). */
  timeout?: number;

  /** API key for hybrid SQL transpilation (from hatidata.com/signup). */
  cloudKey?: string;

  /** HatiData cloud API URL. Defaults to "https://api.hatidata.com". */
  cloudEndpoint?: string;
}

/**
 * Request body for the /v1/transpile endpoint.
 */
export interface TranspileRequest {
  sql: string;
  dialect?: string;
}

/**
 * Response from the /v1/transpile endpoint.
 */
export interface TranspileResponse {
  sql: string;
  hybrid: boolean;
  embeddings_generated: number;
  embedding_dimensions: number;
  quota_remaining: number;
}

/**
 * Column metadata returned with query results.
 */
export interface ColumnInfo {
  /** Column name. */
  name: string;

  /** Column data type (e.g., "VARCHAR", "INTEGER", "BOOLEAN"). */
  type: string;
}

/**
 * Result of a SQL query execution.
 */
export interface QueryResult {
  /** Column metadata for the result set. */
  columns: ColumnInfo[];

  /** Array of row objects, keyed by column name. */
  rows: Record<string, unknown>[];

  /** Number of rows returned or affected. */
  rowCount: number;

  /** Server-side execution time in milliseconds. */
  executionTimeMs: number;
}

/**
 * Options for pushing local data to a remote HatiData instance.
 */
export interface PushOptions {
  /** Target environment to push to. */
  target: "cloud" | "vpc";

  /** List of table names to push. If empty, pushes all tables. */
  tables?: string[];

  /** API key for authenticating with the remote instance. */
  apiKey: string;
}

/**
 * Options for pulling remote schema and data locally.
 */
export interface PullOptions {
  /** List of table names to pull. If empty, pulls all tables. */
  tables?: string[];
}

/**
 * Information about a table in the database.
 */
export interface TableInfo {
  /** Table name. */
  name: string;

  /** Schema name (e.g., "main", "public"). */
  schema: string;

  /** Number of columns in the table. */
  columnCount: number;

  /** Approximate number of rows in the table. */
  rowCount: number;
}

/**
 * Connection state of a HatiData client.
 */
export type ConnectionState =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

// ── Control Plane Types ──────────────────────────────────────────────

/**
 * Configuration for connecting to the HatiData Control Plane.
 */
export interface ControlPlaneConfig {
  /** Control plane URL (e.g., "https://api.hatidata.com"). */
  baseUrl?: string;
  /** User email for JWT login. */
  email?: string;
  /** User password for JWT login. */
  password?: string;
  /** API key (alternative to email/password). */
  apiKey?: string;
  /** Organization ID. Auto-detected from login if not provided. */
  orgId?: string;
  /** Request timeout in milliseconds. Defaults to 15000. */
  timeout?: number;
}

export interface LoginResponse {
  token: string;
  user: { id: string; email: string; role: string; [key: string]: unknown };
  org: { id: string; name: string; tier: string; [key: string]: unknown };
}

export interface AgentMemory {
  id: string;
  org_id: string;
  agent_id: string;
  content: string;
  memory_type: string;
  created_at: string;
  access_count?: number;
  has_embedding?: boolean;
  embedding_model?: string;
  embedding_dimensions?: number;
  embedding_status?: string;
  branch_id?: string;
  [key: string]: unknown;
}

export interface EmbeddingStats {
  total_memories: number;
  embedded_count: number;
  pending_count: number;
  embedding_model: string;
  [key: string]: unknown;
}

export interface SemanticTrigger {
  id: string;
  name: string;
  concept: string;
  threshold: number;
  actions: string[];
  cooldown_secs: number;
  fire_count?: number;
  created_at: string;
  [key: string]: unknown;
}

export interface TriggerTestResult {
  would_fire: boolean;
  similarity: number;
  trigger_name?: string;
  [key: string]: unknown;
}

export interface Branch {
  id: string;
  agent_id: string;
  tables: string[];
  description?: string;
  status: string;
  created_at: string;
  [key: string]: unknown;
}

export interface BranchMergeResult {
  status: string;
  conflicts?: number;
  [key: string]: unknown;
}

export interface BranchDiff {
  tables: Record<string, unknown>;
  [key: string]: unknown;
}

export interface BranchConflicts {
  has_conflicts: boolean;
  conflicts: unknown[];
  [key: string]: unknown;
}

export interface BranchCost {
  storage_bytes: number;
  compute_credits: number;
  [key: string]: unknown;
}

export interface BranchAnalytics {
  total_branches: number;
  active_branches: number;
  [key: string]: unknown;
}

export interface CotTrace {
  trace_id: string;
  session_id: string;
  agent_id: string;
  org_id: string;
  step_index: number;
  trace_type: string;
  content: Record<string, unknown>;
  content_hash: string;
  timestamp: string;
}

export interface CotIngestResult {
  ingested: number;
  session_id: string;
  [key: string]: unknown;
}

export interface CotSession {
  session_id: string;
  agent_id: string;
  total_steps: number;
  started_at: string;
  ended_at?: string;
  [key: string]: unknown;
}

export interface CotReplay {
  session_id: string;
  total_steps: number;
  chain_valid: boolean;
  steps: Array<{
    step_index: number;
    trace_type: string;
    content: Record<string, unknown>;
    content_hash: string;
    [key: string]: unknown;
  }>;
  [key: string]: unknown;
}

export interface CotVerification {
  chain_valid: boolean;
  total_traces: number;
  invalid_hashes: string[];
  [key: string]: unknown;
}

export interface JitGrant {
  id: string;
  requester_id: string;
  org_id: string;
  target_role: string;
  reason: string;
  status: string;
  created_at: string;
  expires_at?: string;
  [key: string]: unknown;
}
