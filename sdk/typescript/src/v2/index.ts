/**
 * HatiData V2 Runtime SDK
 *
 * Governed runtime substrate for production agent systems.
 * Memory, lineage, branching, review, recovery, and replay in one SDK.
 *
 * @example
 * ```typescript
 * import { HatiDataV2Client } from "@hatidata/sdk/v2";
 *
 * const hd = new HatiDataV2Client({
 *   baseUrl: "https://preprod-api.hatidata.com",
 *   token: "hd_live_your_api_key_here",
 * });
 *
 * // Create a task and attempt
 * const task = await hd.runtime.createTask({ kind: "code_generation" });
 * const attempt = await hd.runtime.createAttempt(task.id);
 * const claimed = await hd.runtime.claim(attempt.id, attempt.lease_token, "my-agent");
 *
 * // Record work
 * const decision = await hd.runtime.recordDecision({
 *   attempt_id: attempt.id,
 *   model_id: "claude-sonnet-4-6",
 * });
 *
 * // Publish artifact
 * const artifact = await hd.runtime.publishArtifact({
 *   attempt_id: attempt.id,
 *   kind: "code",
 *   content_hash: "sha256:abc123",
 *   confidence: 0.92,
 * });
 *
 * // Complete
 * await hd.runtime.complete(attempt.id, attempt.lease_token, { outcome: "succeeded" });
 *
 * // Explain the artifact
 * const bundle = await hd.lineage.explain(artifact.id);
 * console.log(`Cost: $${bundle.total_cost_usd}, Decisions: ${bundle.decisions.length}`);
 * ```
 */

export { HatiDataV2Client } from "./client.js";
export type { V2ClientConfig, RuntimeClient, LineageClient, ReviewClient, ViewsClient } from "./client.js";
export * from "./types.js";
