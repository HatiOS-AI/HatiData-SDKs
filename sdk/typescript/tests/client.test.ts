import { describe, it, expect } from "vitest";
import {
  HatiDataClient,
  HatiDataError,
  ConnectionError,
  QueryError,
  AuthenticationError,
  SyncError,
} from "../src/index";
import type {
  HatiDataConfig,
  QueryResult,
  ConnectionState,
} from "../src/index";

describe("HatiDataClient", () => {
  describe("constructor", () => {
    it("should create a client with explicit config", () => {
      const config: HatiDataConfig = {
        host: "db.example.com",
        port: 9090,
        database: "analytics",
        apiKey: "hd_test_key_123",
        ssl: true,
        timeout: 60_000,
      };

      const client = new HatiDataClient(config);
      expect(client).toBeInstanceOf(HatiDataClient);
      expect(client.state).toBe("disconnected");
    });

    it("should create a client with default config values", () => {
      const client = new HatiDataClient({});
      expect(client).toBeInstanceOf(HatiDataClient);
      expect(client.state).toBe("disconnected");
    });

    it("should create a client with only an API key", () => {
      const client = new HatiDataClient({ apiKey: "hd_my_key" });
      expect(client).toBeInstanceOf(HatiDataClient);
      expect(client.state).toBe("disconnected");
    });

    it("should create a client with user/password auth", () => {
      const client = new HatiDataClient({
        user: "admin",
        password: "secret",
      });
      expect(client).toBeInstanceOf(HatiDataClient);
    });
  });

  describe("connection state", () => {
    it("should start in disconnected state", () => {
      const client = new HatiDataClient({});
      expect(client.state).toBe("disconnected" satisfies ConnectionState);
    });

    it("should return to disconnected state after close", async () => {
      const client = new HatiDataClient({});
      await client.close();
      expect(client.state).toBe("disconnected");
    });
  });

  describe("query without connection", () => {
    it("should throw ConnectionError when not connected", async () => {
      const client = new HatiDataClient({});

      await expect(client.query("SELECT 1")).rejects.toThrow(ConnectionError);
      await expect(client.query("SELECT 1")).rejects.toThrow(
        /not connected/i
      );
    });

    it("should throw ConnectionError for listTables when not connected", async () => {
      const client = new HatiDataClient({});

      await expect(client.listTables()).rejects.toThrow(ConnectionError);
    });

    it("should throw ConnectionError for push when not connected", async () => {
      const client = new HatiDataClient({});

      await expect(
        client.push({ target: "cloud", apiKey: "test" })
      ).rejects.toThrow(ConnectionError);
    });

    it("should throw ConnectionError for pull when not connected", async () => {
      const client = new HatiDataClient({});

      await expect(client.pull({ tables: ["t1"] })).rejects.toThrow(
        ConnectionError
      );
    });
  });
});

describe("Error classes", () => {
  it("HatiDataError should have correct name and code", () => {
    const err = new HatiDataError("test error", "TEST_CODE");
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(HatiDataError);
    expect(err.name).toBe("HatiDataError");
    expect(err.code).toBe("TEST_CODE");
    expect(err.message).toBe("test error");
  });

  it("ConnectionError should have correct code", () => {
    const err = new ConnectionError("connection lost");
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(HatiDataError);
    expect(err).toBeInstanceOf(ConnectionError);
    expect(err.name).toBe("ConnectionError");
    expect(err.code).toBe("CONNECTION_FAILED");
    expect(err.message).toBe("connection lost");
  });

  it("QueryError should have correct code and sqlState", () => {
    const err = new QueryError("table not found", "42P01");
    expect(err).toBeInstanceOf(HatiDataError);
    expect(err).toBeInstanceOf(QueryError);
    expect(err.name).toBe("QueryError");
    expect(err.code).toBe("QUERY_ERROR");
    expect(err.sqlState).toBe("42P01");
    expect(err.message).toBe("table not found");
  });

  it("QueryError should work without sqlState", () => {
    const err = new QueryError("syntax error");
    expect(err.sqlState).toBeUndefined();
    expect(err.code).toBe("QUERY_ERROR");
  });

  it("AuthenticationError should have correct code", () => {
    const err = new AuthenticationError("invalid key");
    expect(err).toBeInstanceOf(HatiDataError);
    expect(err).toBeInstanceOf(AuthenticationError);
    expect(err.name).toBe("AuthenticationError");
    expect(err.code).toBe("AUTHENTICATION_FAILED");
  });

  it("SyncError should have correct code", () => {
    const err = new SyncError("push failed");
    expect(err).toBeInstanceOf(HatiDataError);
    expect(err).toBeInstanceOf(SyncError);
    expect(err.name).toBe("SyncError");
    expect(err.code).toBe("SYNC_FAILED");
  });
});

describe("QueryResult type", () => {
  it("should conform to the QueryResult interface", () => {
    const result: QueryResult = {
      columns: [
        { name: "id", type: "INTEGER" },
        { name: "name", type: "VARCHAR" },
      ],
      rows: [
        { id: 1, name: "Alice" },
        { id: 2, name: "Bob" },
      ],
      rowCount: 2,
      executionTimeMs: 12.5,
    };

    expect(result.columns).toHaveLength(2);
    expect(result.columns[0].name).toBe("id");
    expect(result.columns[0].type).toBe("INTEGER");
    expect(result.rows).toHaveLength(2);
    expect(result.rowCount).toBe(2);
    expect(result.executionTimeMs).toBeGreaterThan(0);
  });

  it("should handle empty results", () => {
    const result: QueryResult = {
      columns: [],
      rows: [],
      rowCount: 0,
      executionTimeMs: 1,
    };

    expect(result.columns).toHaveLength(0);
    expect(result.rows).toHaveLength(0);
    expect(result.rowCount).toBe(0);
  });
});
