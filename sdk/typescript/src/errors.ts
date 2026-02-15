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
