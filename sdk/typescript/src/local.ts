import type { QueryResult, TableInfo } from "./types.js";
import { HatiDataError } from "./errors.js";

/**
 * Local query engine backed by DuckDB-WASM.
 *
 * This enables fully offline, in-process SQL execution without connecting
 * to a remote HatiData instance. Ideal for development, testing, and
 * edge/agent workloads.
 *
 * **Requires:** `@duckdb/duckdb-wasm` as a peer dependency.
 * Install it separately: `npm install @duckdb/duckdb-wasm`
 *
 * @example
 * ```typescript
 * const engine = new LocalEngine();
 * await engine.init();
 *
 * await engine.query("CREATE TABLE events (id INT, name VARCHAR)");
 * await engine.query("INSERT INTO events VALUES (1, 'click'), (2, 'view')");
 *
 * const result = await engine.query("SELECT * FROM events");
 * console.log(result.rows);
 *
 * await engine.close();
 * ```
 */
export class LocalEngine {
  /** Path to the DuckDB database file. */
  readonly dbPath: string;
  private initialized = false;
  // DuckDB-WASM types are not available at compile time (optional peer dep).
  // We use `unknown` and cast at runtime after the dynamic import succeeds.
  private db: unknown = null;
  private conn: unknown = null;

  /**
   * Create a new local engine instance.
   *
   * @param dbPath - Path to the DuckDB database file. Defaults to ".hati/local.duckdb".
   *                 Use ":memory:" for a purely in-memory database.
   */
  constructor(dbPath?: string) {
    this.dbPath = dbPath ?? ".hati/local.duckdb";
  }

  /**
   * Initialize the DuckDB-WASM engine.
   *
   * Lazily imports `@duckdb/duckdb-wasm`. If the package is not installed,
   * a helpful error message is thrown with installation instructions.
   *
   * @throws {HatiDataError} If DuckDB-WASM is not installed.
   */
  async init(): Promise<void> {
    if (this.initialized) {
      return;
    }

    try {
      // Dynamic import to keep @duckdb/duckdb-wasm as an optional peer dependency.
      // This avoids bundling the ~10MB WASM binary unless local mode is actually used.
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const duckdb: any = await (Function(
        'return import("@duckdb/duckdb-wasm")'
      )() as Promise<unknown>);

      // DuckDB-WASM initialization follows the library's standard pattern:
      // 1. Select the best available bundle (EH or MVP, with/without threads)
      // 2. Instantiate the async database
      // 3. Open a connection for executing queries
      const DUCKDB_BUNDLES = duckdb.getJsDelivrBundles();
      const bundle = await duckdb.selectBundle(DUCKDB_BUNDLES);

      // Worker is only available in browser environments.
      // Use indexed access to avoid type errors in Node.js typings.
      const WorkerCtor = (globalThis as Record<string, unknown>)[
        "Worker"
      ] as (new (url: string) => unknown) | undefined;
      const worker = WorkerCtor ? new WorkerCtor(bundle.mainWorker!) : null;
      const logger = new duckdb.ConsoleLogger();
      this.db = new duckdb.AsyncDuckDB(logger, worker);

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (this.db as any).instantiate(
        bundle.mainModule,
        bundle.pthreadWorker
      );
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      this.conn = await (this.db as any).connect();
      this.initialized = true;
    } catch (error) {
      if (
        error instanceof Error &&
        (error.message.includes("Cannot find module") ||
          error.message.includes("MODULE_NOT_FOUND") ||
          error.message.includes("Failed to resolve") ||
          error.message.includes("@duckdb/duckdb-wasm"))
      ) {
        throw new HatiDataError(
          "Install @duckdb/duckdb-wasm for local mode: npm install @duckdb/duckdb-wasm",
          "MISSING_DEPENDENCY"
        );
      }

      throw new HatiDataError(
        `Failed to initialize local DuckDB engine: ${error instanceof Error ? error.message : String(error)}`,
        "LOCAL_INIT_FAILED"
      );
    }
  }

  /**
   * Execute a SQL query against the local DuckDB instance.
   *
   * @param sql - SQL statement to execute.
   * @returns Query results with columns, rows, and execution timing.
   * @throws {HatiDataError} If the engine is not initialized or the query fails.
   */
  async query(sql: string): Promise<QueryResult> {
    this.ensureInitialized();

    const startTime = Date.now();

    try {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const result = await (this.conn as any).query(sql);
      const executionTimeMs = Date.now() - startTime;

      // Convert Apache Arrow result to plain objects
      const columns = result.schema.fields.map(
        (field: { name: string; type: { toString(): string } }) => ({
          name: field.name,
          type: field.type.toString(),
        })
      );

      const rows: Record<string, unknown>[] = [];
      for (const row of result) {
        const obj: Record<string, unknown> = {};
        for (const col of columns) {
          obj[col.name] = row[col.name];
        }
        rows.push(obj);
      }

      return {
        columns,
        rows,
        rowCount: rows.length,
        executionTimeMs,
      };
    } catch (error) {
      throw new HatiDataError(
        `Local query failed: ${error instanceof Error ? error.message : String(error)}`,
        "QUERY_ERROR"
      );
    }
  }

  /**
   * List all tables in the local DuckDB instance.
   *
   * @returns Array of table metadata.
   * @throws {HatiDataError} If the engine is not initialized.
   */
  async listTables(): Promise<TableInfo[]> {
    this.ensureInitialized();

    const result = await this.query(
      `SELECT table_schema, table_name
       FROM information_schema.tables
       WHERE table_schema NOT IN ('information_schema', 'pg_catalog')
       ORDER BY table_schema, table_name`
    );

    const tables: TableInfo[] = [];

    for (const row of result.rows) {
      const schema = String(row["table_schema"] ?? "main");
      const name = String(row["table_name"] ?? "");

      // Get column count and approximate row count for each table
      let columnCount = 0;
      let rowCount = 0;

      try {
        const colResult = await this.query(
          `SELECT count(*) as cnt FROM information_schema.columns
           WHERE table_schema = '${schema}' AND table_name = '${name}'`
        );
        columnCount = Number(colResult.rows[0]?.["cnt"] ?? 0);

        const rowResult = await this.query(
          `SELECT count(*) as cnt FROM "${schema}"."${name}"`
        );
        rowCount = Number(rowResult.rows[0]?.["cnt"] ?? 0);
      } catch {
        // If we can't get counts, leave them as 0
      }

      tables.push({ name, schema, columnCount, rowCount });
    }

    return tables;
  }

  /**
   * Close the local DuckDB connection and release resources.
   */
  async close(): Promise<void> {
    if (this.conn) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (this.conn as any).close();
      this.conn = null;
    }
    if (this.db) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (this.db as any).terminate();
      this.db = null;
    }
    this.initialized = false;
  }

  // ── Private helpers ────────────────────────────────────────────────

  private ensureInitialized(): void {
    if (!this.initialized) {
      throw new HatiDataError(
        "Local engine not initialized. Call init() first.",
        "NOT_INITIALIZED"
      );
    }
  }
}
