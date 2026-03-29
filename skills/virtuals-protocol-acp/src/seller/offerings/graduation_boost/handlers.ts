import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";
import * as path from "path";

const ACP_DIR = "/docker/openclaw-taan/data/.openclaw/workspace/skills/virtuals-protocol-acp";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const NEO_WALLET = "0x54b70c4BB03D01FC5f2D7b3790642f1eBEe5118d";
const JOB_TIMEOUT_MS = 300000; // 5 minutes
const POLL_INTERVAL_MS = 10000; // 10 seconds

function runAcp(args: string): any {
  try {
    const result = execSync(
      `cd ${ACP_DIR} && npx tsx bin/acp.ts ${args} --json`,
      { timeout: 30000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
    );
    // Extract JSON from output (skip non-JSON lines)
    const lines = result.trim().split("\n");
    for (let i = lines.length - 1; i >= 0; i--) {
      try {
        return JSON.parse(lines[i]);
      } catch { continue; }
    }
    // Try parsing entire output
    return JSON.parse(result.trim());
  } catch (e: any) {
    const stderr = e.stderr?.toString()?.slice(0, 300) || "";
    const stdout = e.stdout?.toString()?.slice(0, 300) || "";
    throw new Error(`ACP CLI error: ${stderr || stdout || e.message?.slice(0, 200)}`);
  }
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// === validateRequirements ===
export function validateRequirements(request: any): ValidationResult {
  const wallet = request?.target_wallet;
  const offering = request?.target_offering;
  const price = request?.target_offering_price;

  if (!wallet || typeof wallet !== "string" || !/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
    return { valid: false, reason: "target_wallet must be a valid Ethereum address (0x + 40 hex chars)" };
  }
  if (!offering || typeof offering !== "string" || offering.trim().length === 0) {
    return { valid: false, reason: "target_offering must be a non-empty string" };
  }
  if (price === undefined || price === null || typeof price !== "number" || price < 0) {
    return { valid: false, reason: "target_offering_price must be a non-negative number (USDC)" };
  }
  if (price > 100) {
    return { valid: false, reason: "target_offering_price exceeds safety limit of $100 per test" };
  }
  return { valid: true };
}

// === requestAdditionalFunds ===
export function requestAdditionalFunds(request: any): {
  content?: string;
  amount: number;
  tokenAddress: string;
  recipient: string;
} {
  const price = request?.target_offering_price || 0;
  return {
    content: `Graduation Boost: $${price.toFixed(2)} USDC required to cover target offering cost`,
    amount: price,
    tokenAddress: USDC_BASE,
    recipient: NEO_WALLET,
  };
}

// === requestPayment ===
export function requestPayment(request: any): string {
  const offering = request?.target_offering || "unknown";
  const price = request?.target_offering_price || 0;
  return `Graduation Boost accepted: testing "${offering}" ($${price.toFixed(2)} + $0.50 service fee)`;
}

// === executeJob ===
export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const targetWallet = request?.target_wallet;
  const targetOffering = request?.target_offering;
  const targetPrice = request?.target_offering_price || 0;
  const testRequirements = request?.test_requirements || {};
  const startTime = Date.now();

  const report: any = {
    type: "graduation_boost_report",
    value: {
      target_wallet: targetWallet,
      target_offering: targetOffering,
      target_offering_price: targetPrice,
      test_timestamp: new Date().toISOString(),
      test_requirements_sent: testRequirements,
      result: { status: "pending", response_time_ms: 0, job_id: null, phases_completed: [] },
      qa_scores: {},
      overall_score: 0,
      graduation_progress: { this_test: "PENDING", recommendation: "" },
    },
  };

  try {
    // Step 1: Create job on target agent
    const reqJson = JSON.stringify(testRequirements).replace(/'/g, "'\\''");
    const createResult = runAcp(
      `job create ${targetWallet} "${targetOffering}" --requirements '${reqJson}'`
    );
    const jobId = createResult?.data?.jobId || createResult?.jobId;

    if (!jobId) {
      report.value.result.status = "failure";
      report.value.result.error = "Failed to create job — no jobId returned";
      report.value.qa_scores.error_handling = { score: 0, max: 10, note: "Job creation failed" };
      report.value.overall_score = 0;
      report.value.graduation_progress = { this_test: "FAIL", recommendation: "Check that offering name and wallet are correct." };
      return { deliverable: report };
    }

    report.value.result.job_id = jobId;
    report.value.result.phases_completed.push("REQUEST");

    // Step 2: Poll for completion
    const deadline = Date.now() + JOB_TIMEOUT_MS;
    let lastPhase = "REQUEST";
    let deliverable: any = null;

    while (Date.now() < deadline) {
      await sleep(POLL_INTERVAL_MS);

      try {
        const statusResult = runAcp(`job status ${jobId}`);
        const phase = statusResult?.phase || statusResult?.data?.phase;
        const phaseStr = String(phase);

        if (phaseStr && phaseStr !== lastPhase) {
          report.value.result.phases_completed.push(phaseStr);
          lastPhase = phaseStr;
        }

        // Phase 4 = COMPLETED, Phase 5 = REJECTED, Phase 6 = EXPIRED
        if (phase === 4 || phaseStr === "COMPLETED") {
          deliverable = statusResult?.deliverable || statusResult?.data?.deliverable;
          report.value.result.status = "success";
          break;
        }
        if (phase === 5 || phaseStr === "REJECTED") {
          report.value.result.status = "rejected";
          report.value.result.error = "Target agent rejected the job";
          break;
        }
        if (phase === 6 || phaseStr === "EXPIRED") {
          report.value.result.status = "expired";
          report.value.result.error = "Job expired without completion";
          break;
        }
      } catch (pollErr: any) {
        // Non-fatal: continue polling
        console.log(`[graduation_boost] Poll error for job ${jobId}: ${pollErr.message?.slice(0, 100)}`);
      }
    }

    // Check timeout
    if (report.value.result.status === "pending") {
      report.value.result.status = "timeout";
      report.value.result.error = `Job did not complete within ${JOB_TIMEOUT_MS / 1000}s`;
    }

    const responseTime = Date.now() - startTime;
    report.value.result.response_time_ms = responseTime;
    report.value.result.deliverable_received = deliverable
      ? (typeof deliverable === "string" ? deliverable.slice(0, 500) : JSON.stringify(deliverable).slice(0, 500))
      : null;

    // Step 3: QA Scoring
    const isSuccess = report.value.result.status === "success";

    // Response time score (out of 10)
    let timeScore = 10;
    if (responseTime > 240000) timeScore = 2;
    else if (responseTime > 180000) timeScore = 4;
    else if (responseTime > 120000) timeScore = 6;
    else if (responseTime > 60000) timeScore = 8;
    report.value.qa_scores.response_time = {
      score: timeScore,
      max: 10,
      note: `${(responseTime / 1000).toFixed(1)}s`,
    };

    // Completion score
    report.value.qa_scores.completion = {
      score: isSuccess ? 10 : 0,
      max: 10,
      note: isSuccess ? "Job completed successfully" : `Status: ${report.value.result.status}`,
    };

    // Deliverable quality score
    let deliverableScore = 0;
    let deliverableNote = "No deliverable received";
    if (deliverable) {
      const delivStr = typeof deliverable === "string" ? deliverable : JSON.stringify(deliverable);
      if (delivStr.length > 10) { deliverableScore += 4; deliverableNote = "Deliverable present"; }
      if (delivStr.length > 100) { deliverableScore += 3; deliverableNote = "Substantial deliverable"; }
      if (delivStr.length > 500) { deliverableScore += 3; deliverableNote = "Detailed deliverable"; }
    }
    report.value.qa_scores.deliverable_quality = {
      score: Math.min(deliverableScore, 10),
      max: 10,
      note: deliverableNote,
    };

    // Overall score
    const scores = Object.values(report.value.qa_scores) as any[];
    const totalScore = scores.reduce((sum: number, s: any) => sum + (s.score || 0), 0);
    const maxScore = scores.reduce((sum: number, s: any) => sum + (s.max || 0), 0);
    report.value.overall_score = maxScore > 0 ? Math.round((totalScore / maxScore) * 100) : 0;

    // Graduation progress
    report.value.graduation_progress = {
      this_test: isSuccess ? "PASS" : "FAIL",
      recommendation: isSuccess
        ? `Offering "${targetOffering}" passed. ${report.value.overall_score >= 70 ? "Quality is good." : "Consider improving response content."}`
        : `Offering "${targetOffering}" failed (${report.value.result.status}). Fix the issue and retest.`,
    };

  } catch (err: any) {
    report.value.result.status = "error";
    report.value.result.error = err.message?.slice(0, 300);
    report.value.result.response_time_ms = Date.now() - startTime;
    report.value.overall_score = 0;
    report.value.graduation_progress = {
      this_test: "FAIL",
      recommendation: `System error: ${err.message?.slice(0, 100)}. Please retry.`,
    };
  }

  return { deliverable: report };
}
