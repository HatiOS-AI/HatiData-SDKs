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
