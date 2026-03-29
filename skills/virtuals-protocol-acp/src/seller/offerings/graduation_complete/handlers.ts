import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";

const ACP_DIR = "/docker/openclaw-taan/data/.openclaw/workspace/skills/virtuals-protocol-acp";
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const NEO_WALLET = "0x54b70c4BB03D01FC5f2D7b3790642f1eBEe5118d";
const JOB_TIMEOUT_MS = 300000;
const POLL_INTERVAL_MS = 10000;

// === Butler SEO keyword lists ===
const BUTLER_KEYWORDS = [
  "analysis", "report", "data", "trade", "token", "market", "sentiment",
  "price", "strategy", "risk", "alert", "monitor", "evaluate", "predict",
  "optimize", "audit", "test", "verify", "check", "scan", "track",
  "blockchain", "defi", "agent", "ai", "automated", "real-time",
];
const HIGH_VALUE_CATEGORIES = [
  "trading", "analysis", "data", "sentiment", "risk", "defi", "nft",
  "monitoring", "alert", "prediction", "optimization", "security",
  "audit", "evaluation", "report", "automation", "intelligence",
];
const ACTION_VERBS = [
  "provides", "delivers", "returns", "generates", "analyzes", "monitors",
  "evaluates", "scans", "tracks", "predicts", "optimizes", "automates",
];
const TRUST_SIGNALS = [
  "real-time", "automated", "24/7", "proven", "verified", "reliable",
  "accurate", "fast", "instant", "comprehensive", "detailed", "powered by",
  "proprietary", "unique", "first", "specialized", "expert",
];
const PRICE_RANGES: Record<string, { low: number; high: number }> = {
  scan: { low: 0.1, high: 0.5 },
  analysis: { low: 0.3, high: 1.0 },
  report: { low: 0.5, high: 2.0 },
  execution: { low: 0.5, high: 5.0 },
  audit: { low: 0.3, high: 1.0 },
};

// === Helpers ===
function runAcp(args: string): any {
  try {
    const result = execSync(
      `cd ${ACP_DIR} && npx tsx bin/acp.ts ${args} --json`,
      { timeout: 30000, encoding: "utf-8", stdio: ["pipe", "pipe", "pipe"] }
    );
    const lines = result.trim().split("\n");
    for (let i = lines.length - 1; i >= 0; i--) {
      try { return JSON.parse(lines[i]); } catch { continue; }
    }
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

// === Validate ===
export function validateRequirements(request: any): ValidationResult {
  const wallet = request?.target_wallet;
  const offering = request?.target_offering;
  const price = request?.target_offering_price;
  const agentName = request?.agent_name;
  const agentDesc = request?.agent_description;
  const offeringDesc = request?.offering_description;
  const testCount = request?.test_count ?? 3;

  if (!wallet || !/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
    return { valid: false, reason: "target_wallet must be a valid Ethereum address" };
  }
  if (!offering || typeof offering !== "string" || offering.trim().length === 0) {
    return { valid: false, reason: "target_offering is required" };
  }
  if (price === undefined || typeof price !== "number" || price < 0) {
    return { valid: false, reason: "target_offering_price must be a non-negative number" };
  }
  if (price > 100) {
    return { valid: false, reason: "target_offering_price exceeds safety limit of $100" };
  }
  if (typeof testCount !== "number" || testCount < 1 || testCount > 10) {
    return { valid: false, reason: "test_count must be 1-10" };
  }
  if (!agentName || typeof agentName !== "string" || agentName.trim().length === 0) {
    return { valid: false, reason: "agent_name is required for profile SEO analysis" };
  }
  if (!agentDesc || typeof agentDesc !== "string" || agentDesc.trim().length === 0) {
    return { valid: false, reason: "agent_description is required for profile SEO analysis" };
  }
  if (!offeringDesc || typeof offeringDesc !== "string" || offeringDesc.trim().length === 0) {
    return { valid: false, reason: "offering_description is required for offering audit" };
  }
  return { valid: true };
}

// === Request Additional Funds ===
export function requestAdditionalFunds(request: any): {
  content?: string; amount: number; tokenAddress: string; recipient: string;
} {
  const price = request?.target_offering_price || 0;
  const count = request?.test_count ?? 3;
  const total = price * count;
  return {
    content: `Graduation Complete: $${total.toFixed(2)} USDC needed (${count} tests × $${price.toFixed(2)})`,
    amount: total,
    tokenAddress: USDC_BASE,
    recipient: NEO_WALLET,
  };
}

// === Request Payment ===
export function requestPayment(request: any): string {
  const offering = request?.target_offering || "unknown";
  const count = request?.test_count ?? 3;
  return `Graduation Complete accepted: audit + ${count} tests + SEO for "${offering}"`;
}

// ============================================================
// STEP 1: Offering Audit (from offering_audit logic)
// ============================================================
function runOfferingAudit(request: any): any {
  const name = request?.target_offering || "";
  const desc = request?.offering_description || "";
  const price = request?.target_offering_price || 0;
  const schema = request?.offering_requirement_schema || {};
  const descLower = desc.toLowerCase();
  const nameLower = name.toLowerCase();

  const audit: any = { scores: {}, recommendations: [] };

  // Description SEO
  const descWords = desc.split(/\s+/).length;
  const matchedKeywords = BUTLER_KEYWORDS.filter((k) => descLower.includes(k));
  let descScore = 0;
  const descNotes: string[] = [];

  if (descWords < 20) { descNotes.push(`Too short (${descWords} words). Aim for 50-150.`); descScore += 2; }
  else if (descWords < 50) { descNotes.push(`Brief (${descWords} words). Expand to 50-150.`); descScore += 5; }
  else if (descWords <= 200) { descNotes.push(`Good length (${descWords} words).`); descScore += 10; }
  else { descNotes.push(`Long (${descWords} words). Trim to under 200.`); descScore += 7; }

  if (matchedKeywords.length === 0) {
    descNotes.push("No search keywords found. Add: " + BUTLER_KEYWORDS.slice(0, 8).join(", "));
    descScore = Math.max(descScore - 3, 0);
  } else if (matchedKeywords.length < 3) {
    descNotes.push(`${matchedKeywords.length} keyword(s): ${matchedKeywords.join(", ")}. Add more.`);
  } else {
    descNotes.push(`Good keywords: ${matchedKeywords.join(", ")}.`);
    descScore = Math.min(descScore + 2, 10);
  }

  const actionVerbs = ["returns", "provides", "delivers", "generates", "analyzes", "scans", "monitors", "evaluates"];
  const hasAction = actionVerbs.some((v) => descLower.includes(v));
  if (!hasAction) descNotes.push("Add action verbs (returns, provides, delivers).");

  const valueIndicators = ["unique", "first", "only", "best", "powered by", "real-time", "automated", "proprietary"];
  const hasValue = valueIndicators.some((v) => descLower.includes(v));
  if (!hasValue) descNotes.push("Add a unique value proposition.");

  audit.scores.description_seo = { score: Math.min(descScore, 10), max: 10, keywords_found: matchedKeywords, notes: descNotes };

  // Naming
  let nameScore = 5;
  const nameNotes: string[] = [];
  if (nameLower.includes("_")) { nameNotes.push("Good: snake_case naming."); nameScore += 2; }
  if (nameLower.length < 5) { nameNotes.push("Name too short."); nameScore -= 2; }
  else if (nameLower.length > 30) { nameNotes.push("Name too long."); nameScore -= 1; }
  const nameKeywords = BUTLER_KEYWORDS.filter((k) => nameLower.includes(k));
  if (nameKeywords.length > 0) { nameNotes.push(`Keywords in name: ${nameKeywords.join(", ")}.`); nameScore += 2; }
  else { nameNotes.push("Embed a keyword in the name."); }
  audit.scores.naming = { score: Math.max(0, Math.min(nameScore, 10)), max: 10, notes: nameNotes };

  // Pricing
  let priceScore = 5;
  const priceNotes: string[] = [];
  if (price === 0) { priceNotes.push("Free. Consider $0.10-0.50 to signal quality."); priceScore = 6; }
  else if (price <= 0.5) { priceNotes.push(`Low ($${price}). Good for volume.`); priceScore = 8; }
  else if (price <= 2.0) { priceNotes.push(`Moderate ($${price}).`); priceScore = 7; }
  else if (price <= 5.0) { priceNotes.push(`Higher ($${price}). Justify in description.`); priceScore = 5; }
  else { priceNotes.push(`Premium ($${price}). May limit volume.`); priceScore = 3; }
  for (const [category, range] of Object.entries(PRICE_RANGES)) {
    if (descLower.includes(category) || nameLower.includes(category)) {
      if (price < range.low) priceNotes.push(`${category}: typical $${range.low}-$${range.high}. Below average.`);
      else if (price > range.high) priceNotes.push(`${category}: typical $${range.low}-$${range.high}. Above average.`);
      break;
    }
  }
  audit.scores.pricing = { score: priceScore, max: 10, notes: priceNotes };

  // Schema
  let schemaScore = 5;
  const schemaNotes: string[] = [];
  const props = schema?.properties;
  if (!props || Object.keys(props).length === 0) {
    schemaNotes.push("No schema provided. Define typed properties.");
    schemaScore = 3;
  } else {
    const propCount = Object.keys(props).length;
    schemaNotes.push(`${propCount} parameter(s).`);
    if (propCount > 10) { schemaNotes.push("Too many. Simplify."); schemaScore -= 2; }
    let withDesc = 0; let withType = 0;
    for (const [, val] of Object.entries(props) as [string, any][]) {
      if (val?.description) withDesc++;
      if (val?.type) withType++;
    }
    if (withDesc === propCount) { schemaNotes.push("All have descriptions."); schemaScore += 3; }
    else { schemaNotes.push(`${propCount - withDesc} lack descriptions.`); }
    if (withType === propCount) { schemaNotes.push("All have types."); schemaScore += 1; }
  }
  audit.scores.schema_quality = { score: Math.max(0, Math.min(schemaScore, 10)), max: 10, notes: schemaNotes };

  // Overall
  const scores = Object.values(audit.scores) as any[];
  const total = scores.reduce((s: number, x: any) => s + (x.score || 0), 0);
  const maxTotal = scores.reduce((s: number, x: any) => s + (x.max || 0), 0);
  audit.overall_score = maxTotal > 0 ? Math.round((total / maxTotal) * 100) : 0;

  // Recommendations
  const recs: string[] = [];
  if (descWords < 50) recs.push("Expand description to 50-150 words.");
  if (matchedKeywords.length < 3) recs.push("Add more search keywords.");
  if (!hasAction) recs.push("Use action verbs.");
  if (!hasValue) recs.push("Add unique value proposition.");
  if (price > 2.0) recs.push("Consider lowering price for volume.");
  if (!props || Object.keys(props).length === 0) recs.push("Define a requirement schema.");
  audit.recommendations = recs.length > 0 ? recs : ["Well-optimized. Focus on completing jobs."];

  return audit;
}

// ============================================================
// STEP 2: Test Execution (from graduation_boost logic)
// ============================================================
async function runTestJobs(request: any, testCount: number): Promise<any[]> {
  const targetWallet = request?.target_wallet;
  const targetOffering = request?.target_offering;
  const testRequirements = request?.test_requirements || {};
  const results: any[] = [];

  for (let i = 0; i < testCount; i++) {
    const testResult: any = {
      test_number: i + 1,
      status: "pending",
      response_time_ms: 0,
      job_id: null,
      qa_scores: {},
      overall_score: 0,
      pass: false,
    };
    const startTime = Date.now();

    try {
      const reqJson = JSON.stringify(testRequirements).replace(/'/g, "'\\''");
      const createResult = runAcp(
        `job create ${targetWallet} "${targetOffering}" --requirements '${reqJson}'`
      );
      const jobId = createResult?.data?.jobId || createResult?.jobId;

      if (!jobId) {
        testResult.status = "failure";
        testResult.error = "No jobId returned";
        testResult.response_time_ms = Date.now() - startTime;
        results.push(testResult);
        continue;
      }

      testResult.job_id = jobId;

      // Poll for completion
      const deadline = Date.now() + JOB_TIMEOUT_MS;
      let deliverable: any = null;

      while (Date.now() < deadline) {
        await sleep(POLL_INTERVAL_MS);
        try {
          const statusResult = runAcp(`job status ${jobId}`);
          const phase = statusResult?.phase || statusResult?.data?.phase;
          const phaseStr = String(phase);

          if (phase === 4 || phaseStr === "COMPLETED") {
            deliverable = statusResult?.deliverable || statusResult?.data?.deliverable;
            testResult.status = "success";
            break;
          }
          if (phase === 5 || phaseStr === "REJECTED") {
            testResult.status = "rejected";
            testResult.error = "Target agent rejected the job";
            break;
          }
          if (phase === 6 || phaseStr === "EXPIRED") {
            testResult.status = "expired";
            testResult.error = "Job expired";
            break;
          }
        } catch (pollErr: any) {
          // Non-fatal
        }
      }

      if (testResult.status === "pending") {
        testResult.status = "timeout";
        testResult.error = `Timeout (${JOB_TIMEOUT_MS / 1000}s)`;
      }

      const responseTime = Date.now() - startTime;
      testResult.response_time_ms = responseTime;

      // QA Scoring
      const isSuccess = testResult.status === "success";

      let timeScore = 10;
      if (responseTime > 240000) timeScore = 2;
      else if (responseTime > 180000) timeScore = 4;
      else if (responseTime > 120000) timeScore = 6;
      else if (responseTime > 60000) timeScore = 8;
      testResult.qa_scores.response_time = { score: timeScore, max: 10, note: `${(responseTime / 1000).toFixed(1)}s` };

      testResult.qa_scores.completion = { score: isSuccess ? 10 : 0, max: 10, note: isSuccess ? "Completed" : testResult.status };

      let deliverableScore = 0;
      let deliverableNote = "No deliverable";
      if (deliverable) {
        const delivStr = typeof deliverable === "string" ? deliverable : JSON.stringify(deliverable);
        if (delivStr.length > 10) { deliverableScore += 4; deliverableNote = "Present"; }
        if (delivStr.length > 100) { deliverableScore += 3; deliverableNote = "Substantial"; }
        if (delivStr.length > 500) { deliverableScore += 3; deliverableNote = "Detailed"; }
      }
      testResult.qa_scores.deliverable_quality = { score: Math.min(deliverableScore, 10), max: 10, note: deliverableNote };

      const scores = Object.values(testResult.qa_scores) as any[];
      const totalS = scores.reduce((s: number, x: any) => s + (x.score || 0), 0);
      const maxS = scores.reduce((s: number, x: any) => s + (x.max || 0), 0);
      testResult.overall_score = maxS > 0 ? Math.round((totalS / maxS) * 100) : 0;
      testResult.pass = isSuccess;

    } catch (err: any) {
      testResult.status = "error";
      testResult.error = err.message?.slice(0, 200);
      testResult.response_time_ms = Date.now() - startTime;
    }

    results.push(testResult);

    // Brief pause between tests to avoid rate limiting
    if (i < testCount - 1) await sleep(3000);
  }

  return results;
}

// ============================================================
// STEP 3: Profile SEO (from profile_seo logic)
// ============================================================
function runProfileSeo(request: any): any {
  const agentName = request?.agent_name || "";
  const agentDesc = request?.agent_description || "";
  const nameLower = agentName.toLowerCase();
  const descLower = agentDesc.toLowerCase();

  const seo: any = { scores: {}, suggested_rewrites: {} };

  // Name
  let nameScore = 5;
  const nameNotes: string[] = [];
  if (agentName.length < 3) { nameNotes.push("Too short."); nameScore -= 2; }
  else if (agentName.length > 20) { nameNotes.push("Too long."); nameScore -= 1; }
  else { nameNotes.push("Good length."); nameScore += 1; }
  const nameCategories = HIGH_VALUE_CATEGORIES.filter((c) => nameLower.includes(c));
  if (nameCategories.length > 0) { nameNotes.push(`Category keywords: ${nameCategories.join(", ")}.`); nameScore += 2; }
  else { nameNotes.push("No category keywords in name."); }
  if (/^[a-zA-Z]+$/.test(agentName)) { nameNotes.push("Clean, memorable."); nameScore += 1; }
  seo.scores.name = { score: Math.max(0, Math.min(nameScore, 10)), max: 10, notes: nameNotes };

  // Description
  const descWords = agentDesc.split(/\s+/).length;
  let descScore = 0;
  const descNotes: string[] = [];
  if (descWords < 30) { descNotes.push(`Too short (${descWords}). Aim for 80-200.`); descScore += 2; }
  else if (descWords < 80) { descNotes.push(`Brief (${descWords}). Expand to 80-200.`); descScore += 5; }
  else if (descWords <= 250) { descNotes.push(`Good length (${descWords}).`); descScore += 9; }
  else { descNotes.push(`Long (${descWords}). Consider trimming.`); descScore += 6; }

  const matchedCategories = HIGH_VALUE_CATEGORIES.filter((c) => descLower.includes(c));
  if (matchedCategories.length >= 5) { descNotes.push(`Excellent coverage: ${matchedCategories.join(", ")}.`); descScore = Math.min(descScore + 1, 10); }
  else if (matchedCategories.length >= 2) { descNotes.push(`Moderate coverage: ${matchedCategories.join(", ")}.`); }
  else { descNotes.push(`Low coverage (${matchedCategories.length}). Add: ${HIGH_VALUE_CATEGORIES.slice(0, 6).join(", ")}.`); descScore = Math.max(descScore - 2, 0); }

  const matchedActions = ACTION_VERBS.filter((v) => descLower.includes(v));
  if (matchedActions.length >= 3) { descNotes.push(`Good verbs: ${matchedActions.join(", ")}.`); }
  else { descNotes.push(`Add verbs: ${ACTION_VERBS.slice(0, 5).join(", ")}.`); }

  const matchedTrust = TRUST_SIGNALS.filter((t) => descLower.includes(t));
  if (matchedTrust.length >= 2) { descNotes.push(`Trust signals: ${matchedTrust.join(", ")}.`); }
  else { descNotes.push("Add trust signals (real-time, verified, 24/7)."); }

  seo.scores.description = { score: Math.max(0, Math.min(descScore, 10)), max: 10, notes: descNotes };

  // Rewrite suggestions
  const missingKeywords = HIGH_VALUE_CATEGORIES.filter((c) => !descLower.includes(c)).slice(0, 3);
  const missingActions = ACTION_VERBS.filter((v) => !descLower.includes(v)).slice(0, 2);
  const missingTrust = TRUST_SIGNALS.filter((t) => !descLower.includes(t)).slice(0, 2);
  seo.suggested_rewrites = {
    keywords_to_add: missingKeywords,
    action_verbs_to_add: missingActions,
    trust_signals_to_add: missingTrust,
  };

  // Overall
  const scores = Object.values(seo.scores) as any[];
  const total = scores.reduce((s: number, x: any) => s + (x.score || 0), 0);
  const maxTotal = scores.reduce((s: number, x: any) => s + (x.max || 0), 0);
  seo.overall_score = maxTotal > 0 ? Math.round((total / maxTotal) * 100) : 0;

  return seo;
}

// ============================================================
// MAIN: executeJob
// ============================================================
export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const testCount = Math.max(1, Math.min(request?.test_count ?? 3, 10));
  const startTime = Date.now();

  const report: any = {
    type: "graduation_complete_report",
    value: {
      target_wallet: request?.target_wallet,
      target_offering: request?.target_offering,
      timestamp: new Date().toISOString(),
      package_summary: {
        test_count_requested: testCount,
        service_fee: 2.0,
        offering_cost_per_test: request?.target_offering_price || 0,
        total_cost: 2.0 + (request?.target_offering_price || 0) * testCount,
      },
      step1_offering_audit: {},
      step2_test_results: [],
      step3_profile_seo: {},
      graduation_status: {},
      total_time_ms: 0,
    },
  };

  try {
    // Step 1: Offering Audit
    report.value.step1_offering_audit = runOfferingAudit(request);

    // Step 2: Test Jobs
    report.value.step2_test_results = await runTestJobs(request, testCount);

    // Step 3: Profile SEO
    report.value.step3_profile_seo = runProfileSeo(request);

    // Graduation Status Summary
    const testResults = report.value.step2_test_results;
    const passed = testResults.filter((t: any) => t.pass).length;
    const failed = testResults.filter((t: any) => !t.pass).length;
    const avgScore = testResults.length > 0
      ? Math.round(testResults.reduce((s: number, t: any) => s + (t.overall_score || 0), 0) / testResults.length)
      : 0;

    report.value.graduation_status = {
      tests_passed: passed,
      tests_failed: failed,
      tests_total: testCount,
      average_qa_score: avgScore,
      offering_audit_score: report.value.step1_offering_audit.overall_score || 0,
      profile_seo_score: report.value.step3_profile_seo.overall_score || 0,
      graduation_ready: passed >= testCount && (report.value.step1_offering_audit.overall_score || 0) >= 50,
      next_steps: [] as string[],
    };

    // Generate next steps
    const ns = report.value.graduation_status.next_steps;
    if (failed > 0) ns.push(`Fix ${failed} failed test(s) and rerun.`);
    if ((report.value.step1_offering_audit.overall_score || 0) < 50) ns.push("Improve offering based on audit recommendations.");
    if ((report.value.step3_profile_seo.overall_score || 0) < 50) ns.push("Optimize profile based on SEO suggestions.");
    if (passed < 10) ns.push(`${10 - passed} more successful tests needed for Graduation (10 total required).`);
    if (passed >= 10 && failed === 0) ns.push("You have enough passed tests! Record a video demo and submit for Graduation review.");
    if (ns.length === 0) ns.push("Looking great! Continue building job volume for search ranking.");

  } catch (err: any) {
    report.value.error = err.message?.slice(0, 300);
  }

  report.value.total_time_ms = Date.now() - startTime;
  return { deliverable: report };
}
