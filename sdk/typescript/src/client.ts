import type {
  HatiDataConfig,
  QueryResult,
  PushOptions,
  PullOptions,
  TableInfo,
  ConnectionState,
  TranspileRequest,
  TranspileResponse,
} from "./types.js";
import {
  ConnectionError,
  QueryError,
  AuthenticationError,
  SyncError,
  HybridSQLError,
  TranspileQuotaError,
} from "./errors.js";

/** Default configuration values. */
const DEFAULTS = {
  host: "localhost",
  port: 8080,
  database: "default",
  ssl: false,
  timeout: 30_000,
  cloudEndpoint: "https://api.hatidata.com",
} as const;

/** Keywords that indicate hybrid SQL requiring cloud transpilation. */
const HYBRID_SQL_PATTERN =
  /\bJOIN_VECTOR\b|\bsemantic_match\b|\bvector_match\b|\bsemantic_rank\b/i;

/**
 * HatiData client for connecting to a HatiData control plane via HTTP API.
 *
 * @example
 * ```typescript
 * const client = new HatiDataClient({
 *   host: "localhost",
 *   port: 8080,
 *   apiKey: "hd_your_api_key",
 * });
 *
 * await client.connect();
 * const result = await client.query("SELECT * FROM sales LIMIT 10");
 * console.log(result.rows);
 * await client.close();
 * ```
 */
export class HatiDataClient {
  private readonly config: Required<
    Pick<HatiDataConfig, "host" | "port" | "database" | "ssl" | "timeout">
  > &
    HatiDataConfig;
  private _state: ConnectionState = "disconnected";
  private baseUrl: string;
  private abortController: AbortController | null = null;
  private readonly cloudKey: string | undefined;
  private readonly cloudEndpoint: string;

  constructor(config: HatiDataConfig) {
    this.config = {
      ...DEFAULTS,
      ...config,
    };

    const protocol = this.config.ssl ? "https" : "http";
    this.baseUrl = `${protocol}://${this.config.host}:${this.config.port}`;
    this.cloudKey =
      config.cloudKey ?? process.env.HATIDATA_CLOUD_KEY ?? undefined;
    this.cloudEndpoint = (
      config.cloudEndpoint ?? DEFAULTS.cloudEndpoint
    ).replace(/\/$/, "");
  }

  /**
   * Current connection state.
   */
  get state(): ConnectionState {
    return this._state;
  }

  /**
   * Connect to the HatiData control plane and verify the connection.
   *
   * @throws {ConnectionError} If the connection cannot be established.
   * @throws {AuthenticationError} If the API key or credentials are invalid.
   */
  async connect(): Promise<void> {
    if (this._state === "connected") {
      return;
    }

    this._state = "connecting";
    this.abortController = new AbortController();

    try {
      const response = await fetch(`${this.baseUrl}/v1/health`, {
        method: "GET",
        headers: this.buildHeaders(),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (response.status === 401 || response.status === 403) {
        this._state = "error";
        throw new AuthenticationError(
          `Authentication failed: ${response.statusText}`
        );
      }

      if (!response.ok) {
        this._state = "error";
        throw new ConnectionError(
          `Failed to connect to HatiData at ${this.baseUrl}: ${response.status} ${response.statusText}`
        );
      }

      this._state = "connected";
    } catch (error) {
      this._state = "error";

      if (error instanceof AuthenticationError) {
        throw error;
      }

      if (error instanceof TypeError) {
        // fetch throws TypeError for network errors (DNS, connection refused, etc.)
        throw new ConnectionError(
          `Cannot reach HatiData at ${this.baseUrl}: ${error.message}`
        );
      }

      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ConnectionError(
          `Connection to HatiData at ${this.baseUrl} timed out after ${this.config.timeout}ms`
        );
      }

      throw error;
    }
  }

  /**
   * Execute a SQL query against HatiData.
   *
   * @param sql - SQL statement to execute.
   * @param params - Optional parameterized query values.
   * @returns Query results including columns, rows, and execution metadata.
   *
   * @throws {ConnectionError} If not connected.
   * @throws {QueryError} If the query fails.
   * @throws {AuthenticationError} If the session has expired.
   */
  async query(sql: string, params?: unknown[]): Promise<QueryResult> {
    this.ensureConnected();

    // Transparently transpile hybrid SQL if needed
    const effectiveSql = await this.maybeTranspile(sql);

    const startTime = Date.now();

    try {
      const response = await fetch(`${this.baseUrl}/v1/query`, {
        method: "POST",
        headers: {
          ...this.buildHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          sql: effectiveSql,
          params: params ?? [],
          database: this.config.database,
        }),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (response.status === 401 || response.status === 403) {
        this._state = "error";
        throw new AuthenticationError(
          `Authentication failed: ${response.statusText}`
        );
      }

      if (!response.ok) {
        const body = await this.safeReadBody(response);
        throw new QueryError(
          body?.message ?? `Query failed: ${response.status} ${response.statusText}`,
          body?.sqlState
        );
      }

      const body = (await response.json()) as {
        columns?: { name: string; type: string }[];
        rows?: Record<string, unknown>[];
        execution_time_ms?: number;
      };

      const columns = body.columns ?? [];
      const rows = body.rows ?? [];
      const executionTimeMs = body.execution_time_ms ?? Date.now() - startTime;

      return {
        columns,
        rows,
        rowCount: rows.length,
        executionTimeMs,
      };
    } catch (error) {
      if (
        error instanceof QueryError ||
        error instanceof AuthenticationError
      ) {
        throw error;
      }

      if (error instanceof TypeError) {
        this._state = "error";
        throw new ConnectionError(
          `Lost connection to HatiData: ${error.message}`
        );
      }

      if (error instanceof DOMException && error.name === "AbortError") {
        throw new QueryError(
          `Query timed out after ${this.config.timeout}ms`
        );
      }

      throw error;
    }
  }

  /**
   * List all tables accessible in the current database.
   *
   * @returns Array of table metadata.
   * @throws {ConnectionError} If not connected.
   */
  async listTables(): Promise<TableInfo[]> {
    this.ensureConnected();

    try {
      const response = await fetch(
        `${this.baseUrl}/v1/databases/${encodeURIComponent(this.config.database)}/tables`,
        {
          method: "GET",
          headers: this.buildHeaders(),
          signal: AbortSignal.timeout(this.config.timeout),
        }
      );

      if (response.status === 401 || response.status === 403) {
        this._state = "error";
        throw new AuthenticationError(
          `Authentication failed: ${response.statusText}`
        );
      }

      if (!response.ok) {
        throw new ConnectionError(
          `Failed to list tables: ${response.status} ${response.statusText}`
        );
      }

      const body = (await response.json()) as {
        tables?: TableInfo[];
      };

      return body.tables ?? [];
    } catch (error) {
      if (
        error instanceof ConnectionError ||
        error instanceof AuthenticationError
      ) {
        throw error;
      }

      if (error instanceof TypeError) {
        this._state = "error";
        throw new ConnectionError(
          `Lost connection to HatiData: ${error.message}`
        );
      }

      throw error;
    }
  }

  /**
   * Push local tables to a remote HatiData instance (cloud or VPC).
   *
   * **Note:** This API is preliminary and endpoints may change in future releases.
   *
   * @param options - Push configuration including target and table selection.
   * @returns Summary of the sync operation.
   * @throws {ConnectionError} If not connected.
   * @throws {SyncError} If the push operation fails.
   */
  async push(options: PushOptions): Promise<{ tablesSync: number }> {
    this.ensureConnected();

    try {
      const response = await fetch(`${this.baseUrl}/v1/sync/push`, {
        method: "POST",
        headers: {
          ...this.buildHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          target: options.target,
          tables: options.tables ?? [],
          api_key: options.apiKey,
          database: this.config.database,
        }),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (!response.ok) {
        const body = await this.safeReadBody(response);
        throw new SyncError(
          body?.message ?? `Push failed: ${response.status} ${response.statusText}`
        );
      }

      const body = (await response.json()) as {
        tables_synced?: number;
      };

      return { tablesSync: body.tables_synced ?? 0 };
    } catch (error) {
      if (error instanceof SyncError) {
        throw error;
      }

      if (error instanceof TypeError) {
        this._state = "error";
        throw new ConnectionError(
          `Lost connection to HatiData: ${error.message}`
        );
      }

      throw error;
    }
  }

  /**
   * Pull remote schema and data to the local instance.
   *
   * **Note:** This API is preliminary and endpoints may change in future releases.
   *
   * @param options - Pull configuration including table selection.
   * @returns Summary of the pull operation.
   * @throws {ConnectionError} If not connected.
   * @throws {SyncError} If the pull operation fails.
   */
  async pull(options: PullOptions): Promise<{ tablesPulled: number }> {
    this.ensureConnected();

    try {
      const response = await fetch(`${this.baseUrl}/v1/sync/pull`, {
        method: "POST",
        headers: {
          ...this.buildHeaders(),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          tables: options.tables ?? [],
          database: this.config.database,
        }),
        signal: AbortSignal.timeout(this.config.timeout),
      });

      if (!response.ok) {
        const body = await this.safeReadBody(response);
        throw new SyncError(
          body?.message ?? `Pull failed: ${response.status} ${response.statusText}`
        );
      }

      const body = (await response.json()) as {
        tables_pulled?: number;
      };

      return { tablesPulled: body.tables_pulled ?? 0 };
    } catch (error) {
      if (error instanceof SyncError) {
        throw error;
      }

      if (error instanceof TypeError) {
        this._state = "error";
        throw new ConnectionError(
          `Lost connection to HatiData: ${error.message}`
        );
      }

      throw error;
    }
  }

  /**
   * Close the client connection and release resources.
   */
  async close(): Promise<void> {
    if (this.abortController) {
      this.abortController.abort();
      this.abortController = null;
    }
    this._state = "disconnected";
  }

  // ── Private helpers ────────────────────────────────────────────────

  /**
   * Transparently transpile hybrid SQL via the HatiData cloud API.
   * Standard SQL is returned unchanged.
   */
  private async maybeTranspile(sql: string): Promise<string> {
    if (!HYBRID_SQL_PATTERN.test(sql)) {
      return sql;
    }

    if (!this.cloudKey) {
      throw new HybridSQLError(
        "Hybrid SQL (JOIN_VECTOR, semantic_match, etc.) requires a cloud key. " +
          "Get a free key at https://hatidata.com/signup, then pass cloudKey " +
          "to HatiDataClient() or set HATIDATA_CLOUD_KEY env var."
      );
    }

    const response = await fetch(`${this.cloudEndpoint}/v1/transpile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `ApiKey ${this.cloudKey}`,
      },
      body: JSON.stringify({ sql } satisfies TranspileRequest),
      signal: AbortSignal.timeout(this.config.timeout),
    });

    if (response.status === 429) {
      const body = (await response.json()) as {
        error?: string;
        upgrade_url?: string;
      };
      throw new TranspileQuotaError(
        body.error ??
          "Daily hybrid SQL quota exceeded. Upgrade at https://hatidata.com/pricing",
        body.upgrade_url
      );
    }

    if (!response.ok) {
      const text = await response.text();
      throw new HybridSQLError(
        `Transpilation failed (${response.status}): ${text}`
      );
    }

    const result = (await response.json()) as TranspileResponse;
    return result.sql;
  }

  private ensureConnected(): void {
    if (this._state !== "connected") {
      throw new ConnectionError(
        `Client is not connected (state: ${this._state}). Call connect() first.`
      );
    }
  }

  private buildHeaders(): Record<string, string> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      "User-Agent": "@hatidata/sdk/0.1.0",
    };

    if (this.config.apiKey) {
      headers["Authorization"] = `Bearer ${this.config.apiKey}`;
    } else if (this.config.user && this.config.password) {
      const credentials = btoa(`${this.config.user}:${this.config.password}`);
      headers["Authorization"] = `Basic ${credentials}`;
    }

    return headers;
  }

  private async safeReadBody(
    response: Response
  ): Promise<{ message?: string; sqlState?: string } | null> {
    try {
      return (await response.json()) as {
        message?: string;
        sqlState?: string;
      };
    } catch {
      return null;
    }
  }
}
