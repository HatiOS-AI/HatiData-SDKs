/**
 * HatiData V2 Runtime Types
 *
 * Generated from the V2 OpenAPI spec. These types match the REST API
 * response shapes exactly — do not modify manually.
 */

// ── Enums ──────────────────────────────────────────────────────────────

export type TaskStatus = "pending" | "active" | "completed" | "failed" | "cancelled";
export type AttemptStatus = "pending" | "running" | "succeeded" | "failed" | "timed_out" | "cancelled" | "blocked";
export type ArtifactKind = "code" | "document" | "test" | "data" | "deployment" | "schema" | "explain_bundle" | "other";
export type EventKind = "attempt_lifecycle" | "decision_recorded" | "invocation_completed" | "artifact_published" | "validation_recorded" | "confidence_advisory" | "lease_expired" | "recovery_initiated" | "review_requested" | "review_resolved" | "release_decided" | "other";
export type ValidationResult = "pass" | "fail" | "warning" | "skipped";
export type ReviewStatus = "pending" | "in_review" | "approved" | "blocked";
export type ReleaseOutcome = "approved" | "blocked" | "shadow";
export type RecoveryKind = "rollback" | "retry" | "escalate" | "manual";
export type EntityType = "task" | "attempt" | "decision" | "invocation" | "artifact" | "validation" | "event";
export type EdgeKind = "produced_by" | "decided_by" | "invoked_by" | "validated_by" | "triggered" | "depends_on";

// ── Runtime Entities ───────────────────────────────────────────────────

export interface TaskResponse {
  id: string;
  org_id: string;
  kind: string;
  status: TaskStatus;
  project_id?: string;
  max_retries: number;
  metadata: Record<string, unknown>;
  latest_attempt?: AttemptResponse;
  created_at: string;
  updated_at: string;
}

export interface AttemptResponse {
  id: string;
  task_id: string;
  agent_id?: string;
  status: AttemptStatus;
  retry_count: number;
  max_retries: number;
  started_at?: string;
  completed_at?: string;
  failure_reason?: string;
  created_at: string;
}

export interface AttemptWithLeaseResponse extends AttemptResponse {
  lease_token: string;
  lease_expires_at: string;
}

export interface DecisionResponse {
  id: string;
  attempt_id: string;
  model_id: string;
  routing_reason?: string;
  confidence?: number;
  fallback_used: boolean;
  cost_estimate?: number;
  created_at: string;
}

export interface InvocationResponse {
  id: string;
  decision_id: string;
  model_id: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  error?: string;
  created_at: string;
}

export interface ArtifactResponse {
  id: string;
  attempt_id: string;
  kind: ArtifactKind;
  content_hash: string;
  confidence: number;
  validation_status?: ValidationResult;
  artifact_key?: string;
  created_at: string;
}

export interface ValidationResponse {
  id: string;
  artifact_id: string;
  validator_kind: string;
  result: ValidationResult;
  created_at: string;
}

export interface EventResponse {
  id: string;
  attempt_id: string;
  kind: EventKind;
  sequence_num: number;
  payload: Record<string, unknown>;
  created_at: string;
}

// ── Lineage ────────────────────────────────────────────────────────────

export interface LineageGraph {
  root_id: string;
  root_type: EntityType;
  nodes: LineageNode[];
  edges: LineageEdgeSummary[];
  depth: number;
  truncated: boolean;
}

export interface LineageNode {
  id: string;
  entity_type: EntityType;
  label?: string;
  created_at: string;
}

export interface LineageEdgeSummary {
  source_id: string;
  source_type: EntityType;
  target_id: string;
  target_type: EntityType;
  edge_kind: EdgeKind;
}

export interface ExplainBundle {
  artifact: ArtifactSummary;
  attempt?: AttemptSummary;
  task?: TaskSummary;
  decisions: DecisionSummary[];
  invocations: InvocationSummary[];
  validations: ValidationSummary[];
  events: EventSummary[];
  events_truncated: boolean;
  total_events: number;
  branch_id?: string;
  total_cost_usd: number;
  total_tokens: number;
  lineage_depth: number;
  generated_at: string;
}

export interface ArtifactSummary {
  id: string;
  kind: ArtifactKind;
  content_hash: string;
  confidence: number;
  validation_status?: ValidationResult;
  artifact_key?: string;
  created_at: string;
}

export interface AttemptSummary {
  id: string;
  task_id: string;
  agent_id?: string;
  status: AttemptStatus;
  retry_count: number;
  started_at?: string;
  completed_at?: string;
  failure_reason?: string;
}

export interface TaskSummary {
  id: string;
  kind: string;
  status: TaskStatus;
  project_id?: string;
}

export interface DecisionSummary {
  id: string;
  model_id: string;
  routing_reason?: string;
  confidence?: number;
  fallback_used: boolean;
  cost_estimate?: number;
  created_at: string;
}

export interface InvocationSummary {
  id: string;
  decision_id: string;
  model_id: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  error?: string;
  created_at: string;
}

export interface ValidationSummary {
  id: string;
  validator_kind: string;
  result: ValidationResult;
  created_at: string;
}

export interface EventSummary {
  id: string;
  kind: EventKind;
  sequence_num: number;
  payload: Record<string, unknown>;
  created_at: string;
}

// ── Reviews & Governance ───────────────────────────────────────────────

export interface ReviewRequest {
  id: string;
  org_id: string;
  artifact_id?: string;
  attempt_id?: string;
  gate_predicate_id?: string;
  status: ReviewStatus;
  requested_by: string;
  assigned_to?: string;
  evidence_bundle: Record<string, unknown>;
  resolution_reason?: string;
  requested_at: string;
  resolved_at?: string;
  version: number;
}

export interface ReleaseDecision {
  id: string;
  org_id: string;
  artifact_id?: string;
  review_id?: string;
  outcome: ReleaseOutcome;
  evidence_bundle: Record<string, unknown>;
  decided_by: string;
  policy_version: number;
  decided_at: string;
}

export interface RecoveryAction {
  id: string;
  org_id: string;
  attempt_id?: string;
  kind: RecoveryKind;
  trigger_event?: string;
  state_before: Record<string, unknown>;
  state_after: Record<string, unknown>;
  executed_by: string;
  created_at: string;
}

// ── Input Types ────────────────────────────────────────────────────────

export interface CreateTaskInput {
  kind: string;
  project_id?: string;
  max_retries?: number;
  metadata?: Record<string, unknown>;
}

export interface AttemptOutcome {
  outcome: "succeeded" | "failed";
  failure_reason?: string;
}

export interface CreateDecisionInput {
  attempt_id: string;
  model_id: string;
  routing_reason?: string;
  confidence?: number;
  fallback_used?: boolean;
  cost_estimate?: number;
  context?: Record<string, unknown>;
}

export interface CreateInvocationInput {
  decision_id: string;
  model_id: string;
  prompt_hash: string;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number;
  latency_ms: number;
  error?: string;
}

export interface CreateArtifactInput {
  attempt_id: string;
  kind: ArtifactKind;
  content_hash: string;
  confidence: number;
  branch_id?: string;
  artifact_key?: string;
  depends_on?: string[];
  metadata?: Record<string, unknown>;
}

export interface CreateValidationInput {
  validator_kind: string;
  result: ValidationResult;
  evidence?: Record<string, unknown>;
}

export interface CreateEventInput {
  attempt_id: string;
  kind: EventKind;
  payload?: Record<string, unknown>;
}

export interface RequestReviewInput {
  artifact_id?: string;
  attempt_id?: string;
  gate_predicate_id?: string;
  requested_by: string;
  assigned_to?: string;
  evidence_bundle?: Record<string, unknown>;
}

export interface ResolveReviewInput {
  outcome: "approved" | "blocked";
  decided_by: string;
  expected_version: number;
  resolution_reason?: string;
  evidence_bundle?: Record<string, unknown>;
  policy_version?: number;
}

// ── Operator Views ─────────────────────────────────────────────────────

export interface ViewFreshness {
  computed_at: string;
  staleness_ms: number;
  within_slo: boolean;
}

export interface ActiveAttemptsView {
  total_running: number;
  total_pending: number;
  total_blocked: number;
  oldest_attempt_age_secs: number;
  lease_expiry_warnings: number;
  freshness: ViewFreshness;
}

export interface InvocationCostView {
  total_cost_usd: number;
  total_invocations: number;
  total_tokens: number;
  freshness: ViewFreshness;
}

export interface ConfidenceDistributionView {
  total_artifacts: number;
  low_confidence: number;
  medium_confidence: number;
  high_confidence: number;
  p50: number;
  p90: number;
  p99: number;
  freshness: ViewFreshness;
}
