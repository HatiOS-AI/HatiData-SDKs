/**
 * HatiData V2 Runtime Client
 *
 * Thin wrapper over the V2 REST API. All state machine logic lives
 * server-side — this client only handles HTTP and type mapping.
 */

import type {
  TaskResponse,
  AttemptWithLeaseResponse,
  AttemptResponse,
  DecisionResponse,
  InvocationResponse,
  ArtifactResponse,
  ValidationResponse,
  EventResponse,
  LineageGraph,
  ExplainBundle,
  ReviewRequest,
  ReleaseDecision,
  RecoveryAction,
  ActiveAttemptsView,
  InvocationCostView,
  ConfidenceDistributionView,
  CreateTaskInput,
  AttemptOutcome,
  CreateDecisionInput,
  CreateInvocationInput,
  CreateArtifactInput,
  CreateValidationInput,
  CreateEventInput,
  RequestReviewInput,
  ResolveReviewInput,
} from "./types.js";

export interface V2ClientConfig {
  /** Base URL of the HatiData control plane (e.g., https://preprod-api.hatidata.com) */
  baseUrl: string;
  /** API key or JWT token */
  token: string;
  /** Auth scheme: "Bearer" for JWT, "ApiKey" for API keys */
  authScheme?: "Bearer" | "ApiKey";
  /** Request timeout in ms (default: 30000) */
  timeout?: number;
}

export class HatiDataV2Client {
  readonly runtime: RuntimeClient;
  readonly lineage: LineageClient;
  readonly reviews: ReviewClient;
  readonly views: ViewsClient;

  private baseUrl: string;
  private headers: Record<string, string>;
  private timeout: number;

  constructor(config: V2ClientConfig) {
    this.baseUrl = config.baseUrl.replace(/\/$/, "");
    this.timeout = config.timeout ?? 30_000;
    const scheme = config.authScheme ?? "ApiKey";
    this.headers = {
      "Content-Type": "application/json",
      Authorization: `${scheme} ${config.token}`,
    };

    this.runtime = new RuntimeClient(this);
    this.lineage = new LineageClient(this);
    this.reviews = new ReviewClient(this);
    this.views = new ViewsClient(this);
  }

  /** @internal */
  async _fetch<T>(method: string, path: string, body?: unknown): Promise<T> {
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeout);

    try {
      const res = await fetch(url, {
        method,
        headers: this.headers,
        body: body ? JSON.stringify(body) : undefined,
        signal: controller.signal,
      });

      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(`HatiData V2 API error: ${res.status} ${res.statusText} — ${text}`);
      }

      return (await res.json()) as T;
    } finally {
      clearTimeout(timer);
    }
  }
}

// ── Runtime ────────────────────────────────────────────────────────────

export class RuntimeClient {
  constructor(private client: HatiDataV2Client) {}

  async createTask(input: CreateTaskInput): Promise<TaskResponse> {
    return this.client._fetch("POST", "/v2/runtime/tasks", input);
  }

  async getTask(taskId: string): Promise<TaskResponse> {
    return this.client._fetch("GET", `/v2/runtime/tasks/${taskId}`);
  }

  async listTasks(params?: { status?: string; limit?: number; offset?: number }): Promise<TaskResponse[]> {
    const qs = new URLSearchParams();
    if (params?.status) qs.set("status", params.status);
    if (params?.limit) qs.set("limit", String(params.limit));
    if (params?.offset) qs.set("offset", String(params.offset));
    const query = qs.toString() ? `?${qs}` : "";
    return this.client._fetch("GET", `/v2/runtime/tasks${query}`);
  }

  async createAttempt(taskId: string, agentId?: string): Promise<AttemptWithLeaseResponse> {
    return this.client._fetch("POST", `/v2/runtime/tasks/${taskId}/attempts`, { agent_id: agentId });
  }

  async claim(attemptId: string, leaseToken: string, agentId?: string): Promise<AttemptWithLeaseResponse> {
    return this.client._fetch("PUT", `/v2/runtime/attempts/${attemptId}/claim`, {
      lease_token: leaseToken,
      agent_id: agentId,
    });
  }

  async heartbeat(attemptId: string, leaseToken: string): Promise<void> {
    await this.client._fetch("PUT", `/v2/runtime/attempts/${attemptId}/heartbeat`, {
      lease_token: leaseToken,
    });
  }

  async complete(attemptId: string, leaseToken: string, outcome: AttemptOutcome): Promise<AttemptResponse> {
    return this.client._fetch("PUT", `/v2/runtime/attempts/${attemptId}/complete`, {
      lease_token: leaseToken,
      ...outcome,
    });
  }

  async recordDecision(input: CreateDecisionInput): Promise<DecisionResponse> {
    return this.client._fetch("POST", "/v2/runtime/decisions", input);
  }

  async recordInvocation(input: CreateInvocationInput): Promise<InvocationResponse> {
    return this.client._fetch("POST", "/v2/runtime/invocations", input);
  }

  async publishArtifact(input: CreateArtifactInput): Promise<ArtifactResponse> {
    return this.client._fetch("POST", "/v2/runtime/artifacts", input);
  }

  async recordValidation(artifactId: string, input: CreateValidationInput): Promise<ValidationResponse> {
    return this.client._fetch("POST", `/v2/runtime/artifacts/${artifactId}/validations`, input);
  }

  async ingestEvent(input: CreateEventInput): Promise<EventResponse> {
    return this.client._fetch("POST", "/v2/runtime/events", input);
  }
}

// ── Lineage ────────────────────────────────────────────────────────────

export class LineageClient {
  constructor(private client: HatiDataV2Client) {}

  async upstream(entityId: string, params?: { entity_type?: string; depth?: number }): Promise<LineageGraph> {
    const qs = new URLSearchParams();
    if (params?.entity_type) qs.set("entity_type", params.entity_type);
    if (params?.depth) qs.set("depth", String(params.depth));
    const query = qs.toString() ? `?${qs}` : "";
    return this.client._fetch("GET", `/v2/lineage/${entityId}/upstream${query}`);
  }

  async downstream(entityId: string, params?: { entity_type?: string; depth?: number }): Promise<LineageGraph> {
    const qs = new URLSearchParams();
    if (params?.entity_type) qs.set("entity_type", params.entity_type);
    if (params?.depth) qs.set("depth", String(params.depth));
    const query = qs.toString() ? `?${qs}` : "";
    return this.client._fetch("GET", `/v2/lineage/${entityId}/downstream${query}`);
  }

  async explain(artifactId: string, maxEvents?: number): Promise<ExplainBundle> {
    const qs = maxEvents ? `?max_events=${maxEvents}` : "";
    return this.client._fetch("GET", `/v2/explain/${artifactId}${qs}`);
  }
}

// ── Reviews ────────────────────────────────────────────────────────────

export class ReviewClient {
  constructor(private client: HatiDataV2Client) {}

  async requestReview(input: RequestReviewInput): Promise<ReviewRequest> {
    return this.client._fetch("POST", "/v2/reviews", input);
  }

  async approve(reviewId: string, decidedBy: string, expectedVersion: number, reason?: string): Promise<ReviewRequest> {
    return this.client._fetch("PUT", `/v2/reviews/${reviewId}/resolve`, {
      outcome: "approved",
      decided_by: decidedBy,
      expected_version: expectedVersion,
      resolution_reason: reason,
    } satisfies ResolveReviewInput);
  }

  async reject(reviewId: string, decidedBy: string, expectedVersion: number, reason: string): Promise<ReviewRequest> {
    return this.client._fetch("PUT", `/v2/reviews/${reviewId}/resolve`, {
      outcome: "blocked",
      decided_by: decidedBy,
      expected_version: expectedVersion,
      resolution_reason: reason,
    } satisfies ResolveReviewInput);
  }

  async listPending(limit?: number): Promise<ReviewRequest[]> {
    const qs = limit ? `?limit=${limit}` : "";
    return this.client._fetch("GET", `/v2/reviews/pending${qs}`);
  }
}

// ── Operator Views ─────────────────────────────────────────────────────

export class ViewsClient {
  constructor(private client: HatiDataV2Client) {}

  async activeAttempts(): Promise<ActiveAttemptsView> {
    return this.client._fetch("GET", "/v2/runtime/views/active-attempts");
  }

  async invocationCosts(): Promise<InvocationCostView> {
    return this.client._fetch("GET", "/v2/runtime/views/invocation-costs");
  }

  async confidenceDistribution(): Promise<ConfidenceDistributionView> {
    return this.client._fetch("GET", "/v2/runtime/views/confidence-distribution");
  }
}
