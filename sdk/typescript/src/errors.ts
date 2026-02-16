/**
 * Base error class for all HatiData SDK errors.
 */
export class HatiDataError extends Error {
  /** Machine-readable error code (e.g., "CONNECTION_FAILED", "QUERY_ERROR"). */
  readonly code: string;

  constructor(message: string, code: string) {
    super(message);
    this.name = "HatiDataError";
    this.code = code;
    // Restore prototype chain (required for extending built-in classes)
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Thrown when the client cannot establish or maintain a connection.
 */
export class ConnectionError extends HatiDataError {
  constructor(message: string) {
    super(message, "CONNECTION_FAILED");
    this.name = "ConnectionError";
  }
}

/**
 * Thrown when a SQL query fails.
 */
export class QueryError extends HatiDataError {
  /** PostgreSQL-compatible SQLSTATE error code (e.g., "42P01" for undefined table). */
  readonly sqlState?: string;

  constructor(message: string, sqlState?: string) {
    super(message, "QUERY_ERROR");
    this.name = "QueryError";
    this.sqlState = sqlState;
  }
}

/**
 * Thrown when authentication fails (invalid API key, credentials, etc.).
 */
export class AuthenticationError extends HatiDataError {
  constructor(message: string) {
    super(message, "AUTHENTICATION_FAILED");
    this.name = "AuthenticationError";
  }
}

/**
 * Thrown when a push or pull sync operation fails.
 */
export class SyncError extends HatiDataError {
  constructor(message: string) {
    super(message, "SYNC_FAILED");
    this.name = "SyncError";
  }
}

/**
 * Thrown when hybrid SQL is used without a cloud key.
 */
export class HybridSQLError extends HatiDataError {
  constructor(message: string) {
    super(message, "HYBRID_SQL_ERROR");
    this.name = "HybridSQLError";
  }
}

/**
 * Thrown when the daily hybrid SQL transpilation quota is exceeded.
 */
export class TranspileQuotaError extends HatiDataError {
  /** URL to upgrade plan. */
  readonly upgradeUrl: string;

  constructor(message: string, upgradeUrl: string = "https://hatidata.com/pricing") {
    super(message, "QUOTA_EXCEEDED");
    this.name = "TranspileQuotaError";
    this.upgradeUrl = upgradeUrl;
  }
}
