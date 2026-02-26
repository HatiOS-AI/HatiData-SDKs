import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ControlPlaneClient } from "../src/control-plane";
import { AuthenticationError, ConnectionError, HatiDataError } from "../src/errors";
import type {
  ControlPlaneConfig,
  LoginResponse,
  AgentMemory,
  SemanticTrigger,
  Branch,
  CotTrace,
} from "../src/types";

// ── Test helpers ─────────────────────────────────────────────────────

function mockFetch(body: unknown, status = 200) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: () => Promise.resolve(body),
    text: () => Promise.resolve(JSON.stringify(body)),
  } as unknown as Response);
}

function createClient(overrides: Partial<ControlPlaneConfig> = {}): ControlPlaneClient {
  return new ControlPlaneClient({
    baseUrl: "https://cp.test.local",
    email: "test@example.com",
    password: "testpass",
    orgId: "org-001",
    ...overrides,
  });
}

const LOGIN_RESPONSE: LoginResponse = {
  token: "jwt-test-token-123",
  user: { id: "user-001", email: "test@example.com", role: "admin" },
  org: { id: "org-001", name: "Test Org", tier: "cloud" },
};

describe("ControlPlaneClient", () => {
  let originalFetch: typeof globalThis.fetch;

  beforeEach(() => {
    originalFetch = globalThis.fetch;
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  // ── Authentication ───────────────────────────────────────────────

  describe("login", () => {
    it("should authenticate and store token", async () => {
      globalThis.fetch = mockFetch(LOGIN_RESPONSE);
      const cp = createClient();

      const result = await cp.login();

      expect(result.token).toBe("jwt-test-token-123");
      expect(result.user.email).toBe("test@example.com");
      expect(result.org.tier).toBe("cloud");
    });

    it("should auto-detect org ID from login response", async () => {
      globalThis.fetch = mockFetch(LOGIN_RESPONSE);
      const cp = createClient({ orgId: "" });

      await cp.login();

      // Subsequent requests should use the org ID from login
      globalThis.fetch = mockFetch([]);
      await cp.listMemories();

      const lastCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0];
      expect(lastCall[0]).toContain("/v1/organizations/org-001/");
    });

    it("should throw AuthenticationError on 401", async () => {
      globalThis.fetch = mockFetch({}, 401);
      const cp = createClient();

      await expect(cp.login()).rejects.toThrow(AuthenticationError);
    });
  });

  describe("healthCheck", () => {
    it("should return true when healthy", async () => {
      globalThis.fetch = mockFetch({ status: "ok" });
      const cp = createClient();

      const result = await cp.healthCheck();
      expect(result).toBe(true);
    });

    it("should return false on network error", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
      const cp = createClient();

      const result = await cp.healthCheck();
      expect(result).toBe(false);
    });
  });

  describe("API key auth", () => {
    it("should use ApiKey header instead of JWT", async () => {
      globalThis.fetch = mockFetch([]);
      const cp = createClient({ apiKey: "hd_live_test123", orgId: "org-001" });

      await cp.listMemories();

      const headers = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].headers;
      expect(headers["Authorization"]).toBe("ApiKey hd_live_test123");
    });
  });

  // ── Agent Memory ─────────────────────────────────────────────────

  describe("agent memory", () => {
    it("should create a memory", async () => {
      const memory: AgentMemory = {
        id: "mem-001",
        org_id: "org-001",
        agent_id: "agent-1",
        content: "User prefers dark mode",
        memory_type: "observation",
        created_at: "2026-02-26T00:00:00Z",
      };
      // First call = login, second = create
      const fetchMock = vi.fn()
        .mockResolvedValueOnce({
          ok: true, status: 200, statusText: "OK",
          json: () => Promise.resolve(LOGIN_RESPONSE),
          text: () => Promise.resolve(JSON.stringify(LOGIN_RESPONSE)),
        })
        .mockResolvedValueOnce({
          ok: true, status: 200, statusText: "OK",
          json: () => Promise.resolve(memory),
          text: () => Promise.resolve(JSON.stringify(memory)),
        });
      globalThis.fetch = fetchMock;
      const cp = createClient();

      const result = await cp.createMemory({
        agentId: "agent-1",
        content: "User prefers dark mode",
      });

      expect(result.id).toBe("mem-001");
      expect(result.memory_type).toBe("observation");
      // Verify POST body
      const createCall = fetchMock.mock.calls[1];
      const body = JSON.parse(createCall[1].body);
      expect(body.agent_id).toBe("agent-1");
      expect(body.content).toBe("User prefers dark mode");
      expect(body.memory_type).toBe("observation");
    });

    it("should list memories with filters", async () => {
      globalThis.fetch = mockFetch([{ id: "mem-001" }, { id: "mem-002" }]);
      const cp = createClient({ apiKey: "hd_test_key", orgId: "org-001" });

      const result = await cp.listMemories({ agentId: "agent-1", limit: 5 });

      expect(result).toHaveLength(2);
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toContain("agent_id=agent-1");
      expect(url).toContain("limit=5");
    });

    it("should search memories", async () => {
      globalThis.fetch = mockFetch([{ id: "mem-003", content: "dark mode pref" }]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.searchMemory({ query: "dark mode", topK: 3 });

      expect(result).toHaveLength(1);
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toContain("query=dark+mode");
      expect(url).toContain("top_k=3");
    });

    it("should delete a memory", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true, status: 200, statusText: "OK",
        text: () => Promise.resolve("{}"),
      });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.deleteMemory("mem-001");
      expect(result).toEqual({});

      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toContain("/agent-memory/mem-001");
    });

    it("should get embedding stats", async () => {
      const stats = { total_memories: 100, embedded_count: 80, pending_count: 20, embedding_model: "nomic-embed-text-v1.5" };
      globalThis.fetch = mockFetch(stats);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.embeddingStats();
      expect(result.total_memories).toBe(100);
      expect(result.embedded_count).toBe(80);
    });
  });

  // ── Semantic Triggers ────────────────────────────────────────────

  describe("semantic triggers", () => {
    it("should create a trigger", async () => {
      const trigger: SemanticTrigger = {
        id: "trig-001",
        name: "PII Detected",
        concept: "personal data exposure",
        threshold: 0.85,
        actions: ["webhook"],
        cooldown_secs: 60,
        created_at: "2026-02-26T00:00:00Z",
      };
      globalThis.fetch = mockFetch(trigger);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.createTrigger({
        name: "PII Detected",
        concept: "personal data exposure",
      });

      expect(result.id).toBe("trig-001");
      const body = JSON.parse((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
      expect(body.threshold).toBe(0.85);
      expect(body.actions).toEqual(["webhook"]);
    });

    it("should list triggers", async () => {
      globalThis.fetch = mockFetch([{ id: "t1" }, { id: "t2" }]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.listTriggers();
      expect(result).toHaveLength(2);
    });

    it("should test a trigger", async () => {
      globalThis.fetch = mockFetch({ would_fire: true, similarity: 0.92, trigger_name: "PII" });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.testTrigger("trig-001", "User SSN is 123-45-6789");
      expect(result.would_fire).toBe(true);
      expect(result.similarity).toBe(0.92);
    });

    it("should delete a trigger", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true, status: 200, statusText: "OK",
        text: () => Promise.resolve("{}"),
      });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      await cp.deleteTrigger("trig-001");
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toContain("/triggers/trig-001");
    });
  });

  // ── Branches ─────────────────────────────────────────────────────

  describe("branches", () => {
    it("should create a branch", async () => {
      const branch: Branch = {
        id: "br-001",
        agent_id: "agent-1",
        tables: ["portfolio"],
        description: "Conservative strategy",
        status: "active",
        created_at: "2026-02-26T00:00:00Z",
      };
      globalThis.fetch = mockFetch(branch);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.createBranch({
        agentId: "agent-1",
        tables: ["portfolio"],
        description: "Conservative strategy",
      });

      expect(result.id).toBe("br-001");
      expect(result.status).toBe("active");
    });

    it("should list branches", async () => {
      globalThis.fetch = mockFetch([{ id: "br-001" }, { id: "br-002" }]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.listBranches();
      expect(result).toHaveLength(2);
    });

    it("should get a branch by ID", async () => {
      globalThis.fetch = mockFetch({ id: "br-001", status: "active" });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.getBranch("br-001");
      expect(result.id).toBe("br-001");
    });

    it("should merge a branch", async () => {
      globalThis.fetch = mockFetch({ status: "merged", conflicts: 0 });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.mergeBranch("br-001", "branch_wins");
      expect(result.status).toBe("merged");

      const body = JSON.parse((globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].body);
      expect(body.strategy).toBe("branch_wins");
    });

    it("should discard a branch", async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true, status: 200, statusText: "OK",
        text: () => Promise.resolve("{}"),
      });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      await cp.discardBranch("br-001");
      const method = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][1].method;
      expect(method).toBe("DELETE");
    });

    it("should get branch diff", async () => {
      globalThis.fetch = mockFetch({ tables: { portfolio: { added: 3, removed: 1 } } });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.branchDiff("br-001");
      expect(result.tables).toBeDefined();
    });

    it("should check branch conflicts", async () => {
      globalThis.fetch = mockFetch({ has_conflicts: false, conflicts: [] });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.branchConflicts("br-001");
      expect(result.has_conflicts).toBe(false);
    });

    it("should get branch cost", async () => {
      globalThis.fetch = mockFetch({ storage_bytes: 1024, compute_credits: 0.5 });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.branchCost("br-001");
      expect(result.storage_bytes).toBe(1024);
    });

    it("should get branch analytics", async () => {
      globalThis.fetch = mockFetch({ total_branches: 10, active_branches: 3 });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.branchAnalytics();
      expect(result.total_branches).toBe(10);
    });
  });

  // ── Chain-of-Thought ─────────────────────────────────────────────

  describe("chain-of-thought", () => {
    it("should ingest CoT traces", async () => {
      globalThis.fetch = mockFetch({ ingested: 3, session_id: "sess-001" });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const traces: CotTrace[] = [
        {
          trace_id: "t1", session_id: "sess-001", agent_id: "a1",
          org_id: "org-001", step_index: 0, trace_type: "Thought",
          content: { text: "thinking" }, content_hash: "abc", timestamp: "2026-01-01T00:00:00Z",
        },
      ];
      const result = await cp.ingestCot(traces);

      expect(result.ingested).toBe(3);
      // Verify absolute URL (not org-scoped)
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toContain("/v1/cot/ingest");
      expect(url).not.toContain("/organizations/");
    });

    it("should list CoT sessions", async () => {
      globalThis.fetch = mockFetch([{ session_id: "s1" }, { session_id: "s2" }]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.listCotSessions();
      expect(result).toHaveLength(2);
    });

    it("should replay a CoT session", async () => {
      const replay = {
        session_id: "s1", total_steps: 5, chain_valid: true,
        steps: [{ step_index: 0, trace_type: "Thought", content: {}, content_hash: "h1" }],
      };
      globalThis.fetch = mockFetch(replay);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.replayCot("s1");
      expect(result.chain_valid).toBe(true);
      expect(result.total_steps).toBe(5);
    });

    it("should verify a CoT session", async () => {
      globalThis.fetch = mockFetch({ chain_valid: true, total_traces: 5, invalid_hashes: [] });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.verifyCot("s1");
      expect(result.chain_valid).toBe(true);
      expect(result.invalid_hashes).toHaveLength(0);
    });
  });

  // ── JIT Access ───────────────────────────────────────────────────

  describe("JIT access", () => {
    it("should request JIT access", async () => {
      globalThis.fetch = mockFetch({
        id: "jit-001", requester_id: "user-001", org_id: "org-001",
        target_role: "admin", reason: "deploy fix", status: "pending",
        created_at: "2026-02-26T00:00:00Z",
      });
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.requestJit({
        targetRole: "admin",
        reason: "deploy fix",
        durationHours: 2,
      });

      expect(result.id).toBe("jit-001");
      expect(result.status).toBe("pending");
    });

    it("should list JIT grants", async () => {
      globalThis.fetch = mockFetch([{ id: "jit-001" }]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      const result = await cp.listJitGrants();
      expect(result).toHaveLength(1);
    });
  });

  // ── CoT Hash Chain Helpers ───────────────────────────────────────

  describe("buildCotTrace", () => {
    it("should build a trace with SHA-256 hash", () => {
      const trace = ControlPlaneClient.buildCotTrace({
        sessionId: "sess-001",
        agentId: "agent-1",
        orgId: "org-001",
        stepIndex: 0,
        stepType: "Thought",
        content: { text: "thinking" },
      });

      expect(trace.session_id).toBe("sess-001");
      expect(trace.agent_id).toBe("agent-1");
      expect(trace.step_index).toBe(0);
      expect(trace.trace_type).toBe("Thought");
      expect(trace.content_hash).toHaveLength(64); // SHA-256 hex
      expect(trace.trace_id).toBeTruthy();
      expect(trace.timestamp).toBeTruthy();
    });

    it("should chain hashes using prevHash", () => {
      const trace1 = ControlPlaneClient.buildCotTrace({
        sessionId: "s1", agentId: "a1", orgId: "o1",
        stepIndex: 0, stepType: "Thought", content: { text: "step 1" },
      });

      const trace2 = ControlPlaneClient.buildCotTrace({
        sessionId: "s1", agentId: "a1", orgId: "o1",
        stepIndex: 1, stepType: "ToolCall", content: { tool: "search" },
        prevHash: trace1.content_hash,
      });

      expect(trace2.content_hash).not.toBe(trace1.content_hash);
      expect(trace2.content_hash).toHaveLength(64);
    });
  });

  describe("buildCotSession", () => {
    it("should build a complete hash-chained session", () => {
      const [sessionId, traces] = ControlPlaneClient.buildCotSession({
        agentId: "agent-1",
        orgId: "org-001",
        steps: [
          { type: "Thought", content: { text: "thinking" } },
          { type: "ToolCall", content: { tool: "search", query: "test" } },
          { type: "ToolResult", content: { results: 5 } },
          { type: "LlmResponse", content: { text: "done" } },
        ],
      });

      expect(sessionId).toBeTruthy();
      expect(traces).toHaveLength(4);
      expect(traces[0].step_index).toBe(0);
      expect(traces[3].step_index).toBe(3);

      // Verify all traces share the session ID
      for (const t of traces) {
        expect(t.session_id).toBe(sessionId);
        expect(t.agent_id).toBe("agent-1");
        expect(t.org_id).toBe("org-001");
      }

      // Verify each hash is unique (chain is actually chaining)
      const hashes = new Set(traces.map((t) => t.content_hash));
      expect(hashes.size).toBe(4);
    });
  });

  // ── Error handling ───────────────────────────────────────────────

  describe("error handling", () => {
    it("should throw ConnectionError on network failure", async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("fetch failed"));
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      await expect(cp.listMemories()).rejects.toThrow(ConnectionError);
    });

    it("should throw HatiDataError on 500", async () => {
      globalThis.fetch = mockFetch({ error: "internal" }, 500);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      await expect(cp.listMemories()).rejects.toThrow(HatiDataError);
    });

    it("should throw AuthenticationError on 403", async () => {
      globalThis.fetch = mockFetch({ error: "forbidden" }, 403);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-001" });

      await expect(cp.listMemories()).rejects.toThrow(AuthenticationError);
    });
  });

  // ── URL building ─────────────────────────────────────────────────

  describe("URL building", () => {
    it("should build org-scoped URLs correctly", async () => {
      globalThis.fetch = mockFetch([]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-123" });

      await cp.listTriggers();
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toBe("https://cp.test.local/v1/organizations/org-123/triggers");
    });

    it("should build absolute URLs for CoT endpoints", async () => {
      globalThis.fetch = mockFetch([]);
      const cp = createClient({ apiKey: "hd_test", orgId: "org-123" });

      await cp.listCotSessions();
      const url = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls[0][0];
      expect(url).toBe("https://cp.test.local/v1/cot/sessions");
    });
  });
});
