/**
 * HatiData Control Plane client — agent-native features.
 *
 * Wraps the Control Plane REST API for agent memory, semantic triggers,
 * branches, chain-of-thought, and JIT access.
 *
 * @example
 * ```typescript
 * import { ControlPlaneClient } from "@hatidata/sdk";
 *
 * const cp = new ControlPlaneClient({
 *   baseUrl: "https://staging-api.hatidata.com",
 *   email: "sam@nexaflow.demo.hatidata.dev",
 *   password: "DemoDay2026!",
 * });
 *
 * await cp.login();
 * const mem = await cp.createMemory({ agentId: "my-agent", content: "User prefers dark mode" });
 * const results = await cp.searchMemory({ query: "user preferences" });
 * ```
 */

import { createHash, randomUUID } from "node:crypto";
import { AuthenticationError, ConnectionError, HatiDataError } from "./errors.js";
import type {
  ControlPlaneConfig,
  LoginResponse,
  AgentMemory,
  SemanticTrigger,
  TriggerTestResult,
  Branch,
  BranchMergeResult,
  BranchDiff,
  BranchConflicts,
  BranchCost,
  BranchAnalytics,
  CotIngestResult,
  CotSession,
  CotReplay,
  CotVerification,
  JitGrant,
  CotTrace,
  EmbeddingStats,
} from "./types.js";

const DEFAULT_TIMEOUT = 15_000;

export class ControlPlaneClient {
  private readonly baseUrl: string;
  private readonly email: string;
  private readonly password: string;
  private readonly apiKey: string;
  private readonly timeout: number;
  private orgId: string;
  private token: string | null = null;

  constructor(config: ControlPlaneConfig) {
    this.baseUrl = (config.baseUrl ?? "http://localhost:8080").replace(/\/+$/, "");
    this.email = config.email ?? "";
    this.password = config.password ?? "";
    this.apiKey = config.apiKey ?? "";
    this.orgId = config.orgId ?? "";
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT;
  }

  // ── Authentication ─────────────────────────────────────────────────

  /**
   * Authenticate with email/password and store JWT token.
   * Returns the full login response (token, user, org).
   */
  async login(): Promise<LoginResponse> {
    const resp = await this.fetchJson<LoginResponse>(
      `${this.baseUrl}/v1/auth/login`,
      {
        method: "POST",
        body: JSON.stringify({ email: this.email, password: this.password }),
      },
    );
    this.token = resp.token;
    if (!this.orgId && resp.org?.id) {
      this.orgId = resp.org.id;
    }
    return resp;
  }

  /**
   * Check if the control plane is reachable.
   */
  async healthCheck(): Promise<boolean> {
    try {
      const resp = await fetch(`${this.baseUrl}/health`, {
        signal: AbortSignal.timeout(5_000),
      });
      return resp.ok;
    } catch {
      return false;
    }
  }

  // ── Agent Memory ───────────────────────────────────────────────────

  async createMemory(opts: {
    agentId: string;
    content: string;
    memoryType?: string;
  }): Promise<AgentMemory> {
    return this.post("/agent-memory", {
      agent_id: opts.agentId,
      content: opts.content,
      memory_type: opts.memoryType ?? "observation",
    });
  }

  async listMemories(opts?: {
    agentId?: string;
    memoryType?: string;
    limit?: number;
  }): Promise<AgentMemory[]> {
    const params: Record<string, string> = {};
    if (opts?.agentId) params["agent_id"] = opts.agentId;
    if (opts?.memoryType) params["memory_type"] = opts.memoryType;
    if (opts?.limit) params["limit"] = String(opts.limit);
    return this.get("/agent-memory", params);
  }

  async searchMemory(opts: {
    query: string;
    agentId?: string;
    topK?: number;
  }): Promise<AgentMemory[]> {
    const params: Record<string, string> = {
      query: opts.query,
      top_k: String(opts.topK ?? 10),
    };
    if (opts.agentId) params["agent_id"] = opts.agentId;
    return this.get("/agent-memory/search", params);
  }

  async deleteMemory(memoryId: string): Promise<Record<string, unknown>> {
    return this.del(`/agent-memory/${memoryId}`);
  }

  async embeddingStats(): Promise<EmbeddingStats> {
    return this.get("/agent-memory/embedding-stats");
  }

  // ── Semantic Triggers ──────────────────────────────────────────────

  async createTrigger(opts: {
    name: string;
    concept: string;
    threshold?: number;
    actions?: string[];
    cooldownSecs?: number;
  }): Promise<SemanticTrigger> {
    return this.post("/triggers", {
      name: opts.name,
      concept: opts.concept,
      threshold: opts.threshold ?? 0.85,
      actions: opts.actions ?? ["webhook"],
      cooldown_secs: opts.cooldownSecs ?? 60,
    });
  }

  async listTriggers(): Promise<SemanticTrigger[]> {
    return this.get("/triggers");
  }

  async testTrigger(triggerId: string, text: string): Promise<TriggerTestResult> {
    return this.post(`/triggers/${triggerId}/test`, { text });
  }

  async deleteTrigger(triggerId: string): Promise<Record<string, unknown>> {
    return this.del(`/triggers/${triggerId}`);
  }

  // ── Branches ───────────────────────────────────────────────────────

  async createBranch(opts: {
    agentId: string;
    tables: string[];
    description?: string;
  }): Promise<Branch> {
    const payload: Record<string, unknown> = {
      agent_id: opts.agentId,
      tables: opts.tables,
    };
    if (opts.description) payload["description"] = opts.description;
    return this.post("/branches", payload);
  }

  async listBranches(): Promise<Branch[]> {
    return this.get("/branches");
  }

  async getBranch(branchId: string): Promise<Branch> {
    return this.get(`/branches/${branchId}`);
  }

  async mergeBranch(
    branchId: string,
    strategy: string = "branch_wins",
  ): Promise<BranchMergeResult> {
    return this.post(`/branches/${branchId}/merge`, { strategy });
  }

  async discardBranch(branchId: string): Promise<Record<string, unknown>> {
    return this.del(`/branches/${branchId}`);
  }

  async branchDiff(branchId: string): Promise<BranchDiff> {
    return this.get(`/branches/${branchId}/diff`);
  }

  async branchConflicts(branchId: string): Promise<BranchConflicts> {
    return this.get(`/branches/${branchId}/conflicts`);
  }

  async branchCost(branchId: string): Promise<BranchCost> {
    return this.get(`/branches/${branchId}/cost`);
  }

  async branchAnalytics(): Promise<BranchAnalytics> {
    return this.get("/branches/analytics");
  }

  // ── Chain-of-Thought ───────────────────────────────────────────────

  async ingestCot(traces: CotTrace[]): Promise<CotIngestResult> {
    return this.absPost("/v1/cot/ingest", { traces });
  }

  async listCotSessions(): Promise<CotSession[]> {
    return this.absGet("/v1/cot/sessions");
  }

  async replayCot(sessionId: string): Promise<CotReplay> {
    return this.absGet(`/v1/cot/sessions/${sessionId}/replay`);
  }

  async verifyCot(sessionId: string): Promise<CotVerification> {
    return this.absGet(`/v1/cot/sessions/${sessionId}/verify`);
  }

  // ── JIT Access ─────────────────────────────────────────────────────

  async requestJit(opts: {
    targetRole: string;
    reason: string;
    durationHours?: number;
  }): Promise<JitGrant> {
    return this.post("/jit/request", {
      target_role: opts.targetRole,
      reason: opts.reason,
      duration_hours: opts.durationHours ?? 1,
    });
  }

  async listJitGrants(): Promise<JitGrant[]> {
    return this.get("/jit");
  }

  // ── CoT Hash Chain Helpers ─────────────────────────────────────────

  /**
   * Build a single CoT trace entry with SHA-256 hash chain.
   */
  static buildCotTrace(opts: {
    sessionId: string;
    agentId: string;
    orgId: string;
    stepIndex: number;
    stepType: string;
    content: Record<string, unknown>;
    prevHash?: string;
  }): CotTrace {
    const traceId = randomUUID();
    const timestamp = new Date().toISOString();
    const hashInput = `${opts.prevHash ?? ""}${opts.stepType}${JSON.stringify(opts.content)}${timestamp}`;
    const contentHash = createHash("sha256").update(hashInput).digest("hex");
    return {
      trace_id: traceId,
      session_id: opts.sessionId,
      agent_id: opts.agentId,
      org_id: opts.orgId,
      step_index: opts.stepIndex,
      trace_type: opts.stepType,
      content: opts.content,
      content_hash: contentHash,
      timestamp,
    };
  }

  /**
   * Build a complete CoT session with hash-chained steps.
   *
   * @returns Tuple of [sessionId, traces].
   */
  static buildCotSession(opts: {
    agentId: string;
    orgId: string;
    steps: Array<{ type: string; content: Record<string, unknown> }>;
  }): [string, CotTrace[]] {
    const sessionId = randomUUID();
    const traces: CotTrace[] = [];
    let prevHash = "";
    for (let i = 0; i < opts.steps.length; i++) {
      const step = opts.steps[i];
      const trace = ControlPlaneClient.buildCotTrace({
        sessionId,
        agentId: opts.agentId,
        orgId: opts.orgId,
        stepIndex: i,
        stepType: step.type,
        content: step.content,
        prevHash,
      });
      prevHash = trace.content_hash;
      traces.push(trace);
    }
    return [sessionId, traces];
  }

  // ── Private Helpers ────────────────────────────────────────────────

  private async ensureAuth(): Promise<Record<string, string>> {
    if (this.apiKey) {
      return { Authorization: `ApiKey ${this.apiKey}` };
    }
    if (!this.token) {
      await this.login();
    }
    return { Authorization: `Bearer ${this.token}` };
  }

  private orgUrl(path: string): string {
    return `${this.baseUrl}/v1/organizations/${this.orgId}${path}`;
  }

  private async get<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(this.orgUrl(path));
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
      }
    }
    const headers = await this.ensureAuth();
    return this.fetchJson<T>(url.toString(), {
      method: "GET",
      headers,
    });
  }

  private async post<T>(path: string, body: unknown): Promise<T> {
    const headers = await this.ensureAuth();
    return this.fetchJson<T>(this.orgUrl(path), {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async del<T>(path: string): Promise<T> {
    const headers = await this.ensureAuth();
    const resp = await fetch(this.orgUrl(path), {
      method: "DELETE",
      headers: { ...headers, Accept: "application/json" },
      signal: AbortSignal.timeout(this.timeout),
    });
    this.checkStatus(resp);
    const text = await resp.text();
    return text ? (JSON.parse(text) as T) : ({} as T);
  }

  private async absGet<T>(path: string, params?: Record<string, string>): Promise<T> {
    const url = new URL(`${this.baseUrl}${path}`);
    if (params) {
      for (const [k, v] of Object.entries(params)) {
        url.searchParams.set(k, v);
      }
    }
    const headers = await this.ensureAuth();
    return this.fetchJson<T>(url.toString(), {
      method: "GET",
      headers,
    });
  }

  private async absPost<T>(path: string, body: unknown): Promise<T> {
    const headers = await this.ensureAuth();
    return this.fetchJson<T>(`${this.baseUrl}${path}`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
  }

  private async fetchJson<T>(
    url: string,
    init: RequestInit,
  ): Promise<T> {
    const headers: Record<string, string> = {
      Accept: "application/json",
      "User-Agent": "@hatidata/sdk/0.2.0",
      ...(init.headers as Record<string, string> | undefined),
    };

    let resp: Response;
    try {
      resp = await fetch(url, {
        ...init,
        headers,
        signal: AbortSignal.timeout(this.timeout),
      });
    } catch (error) {
      if (error instanceof TypeError) {
        throw new ConnectionError(`Cannot reach HatiData at ${url}: ${error.message}`);
      }
      if (error instanceof DOMException && error.name === "AbortError") {
        throw new ConnectionError(`Request to ${url} timed out after ${this.timeout}ms`);
      }
      throw error;
    }

    this.checkStatus(resp);
    return (await resp.json()) as T;
  }

  private checkStatus(resp: Response): void {
    if (resp.status === 401 || resp.status === 403) {
      throw new AuthenticationError(`Authentication failed: ${resp.status} ${resp.statusText}`);
    }
    if (!resp.ok) {
      throw new HatiDataError(
        `Request failed: ${resp.status} ${resp.statusText}`,
        "API_ERROR",
      );
    }
  }
}
