import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";

// Butler search ranking factors (from Vertex AI Search investigation):
// 1. Keyword + embedding hybrid search on description
// 2. Reranked by: success rate, unique buyer count, job volume, SLA, ratings, online status
// 3. Description quality directly impacts keyword/embedding match

const BUTLER_KEYWORDS = [
  "analysis", "report", "data", "trade", "token", "market", "sentiment",
  "price", "strategy", "risk", "alert", "monitor", "evaluate", "predict",
  "optimize", "audit", "test", "verify", "check", "scan", "track",
  "blockchain", "defi", "agent", "ai", "automated", "real-time",
];

const PRICE_RANGES: Record<string, { low: number; high: number }> = {
  scan: { low: 0.1, high: 0.5 },
  analysis: { low: 0.3, high: 1.0 },
  report: { low: 0.5, high: 2.0 },
  execution: { low: 0.5, high: 5.0 },
  audit: { low: 0.3, high: 1.0 },
};

export function validateRequirements(request: any): ValidationResult {
  const wallet = request?.target_wallet;
  const name = request?.offering_name;
  const desc = request?.offering_description;
  const price = request?.offering_price;

  if (!wallet || !/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
    return { valid: false, reason: "target_wallet must be a valid Ethereum address" };
  }
  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return { valid: false, reason: "offering_name is required" };
  }
  if (!desc || typeof desc !== "string" || desc.trim().length === 0) {
    return { valid: false, reason: "offering_description is required" };
  }
  if (price === undefined || typeof price !== "number" || price < 0) {
    return { valid: false, reason: "offering_price must be a non-negative number" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  return `Offering audit accepted: analyzing "${request?.offering_name || "unknown"}"`;
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const name = request?.offering_name || "";
  const desc = request?.offering_description || "";
  const price = request?.offering_price || 0;
  const schema = request?.offering_requirement_schema || {};
  const descLower = desc.toLowerCase();
  const nameLower = name.toLowerCase();

  const audit: any = {
    type: "offering_audit_report",
    value: {
      offering_name: name,
      audit_timestamp: new Date().toISOString(),
      scores: {},
      recommendations: [],
      overall_score: 0,
    },
  };

  // === 1. Description SEO Analysis ===
  const descWords = desc.split(/\s+/).length;
  const matchedKeywords = BUTLER_KEYWORDS.filter((k) => descLower.includes(k));
  const keywordDensity = descWords > 0 ? matchedKeywords.length / descWords : 0;

  let descScore = 0;
  const descNotes: string[] = [];

  // Length check (ideal: 50-200 words)
  if (descWords < 20) {
    descNotes.push(`Description too short (${descWords} words). Aim for 50-150 words for best Butler search visibility.`);
    descScore += 2;
  } else if (descWords < 50) {
    descNotes.push(`Description is brief (${descWords} words). Consider expanding to 50-150 words.`);
    descScore += 5;
  } else if (descWords <= 200) {
    descNotes.push(`Good description length (${descWords} words).`);
    descScore += 10;
  } else {
    descNotes.push(`Description may be too long (${descWords} words). Consider trimming to under 200 words.`);
    descScore += 7;
  }

  // Keyword presence
  if (matchedKeywords.length === 0) {
    descNotes.push("No high-value search keywords found. Add terms like: " + BUTLER_KEYWORDS.slice(0, 8).join(", "));
    descScore = Math.max(descScore - 3, 0);
  } else if (matchedKeywords.length < 3) {
    descNotes.push(`Found ${matchedKeywords.length} search keyword(s): ${matchedKeywords.join(", ")}. Add more for wider discoverability.`);
  } else {
    descNotes.push(`Good keyword coverage: ${matchedKeywords.join(", ")} (${matchedKeywords.length} matches).`);
    descScore = Math.min(descScore + 2, 10);
  }

  // Action-oriented language
  const actionVerbs = ["returns", "provides", "delivers", "generates", "analyzes", "scans", "monitors", "evaluates"];
  const hasAction = actionVerbs.some((v) => descLower.includes(v));
  if (!hasAction) {
    descNotes.push("Add action verbs (returns, provides, delivers) to clarify what the buyer gets.");
  }

  // Unique value proposition
  const valueIndicators = ["unique", "first", "only", "best", "powered by", "real-time", "automated", "proprietary"];
  const hasValue = valueIndicators.some((v) => descLower.includes(v));
  if (!hasValue) {
    descNotes.push("Consider adding a unique value proposition to stand out in search results.");
  }

  audit.value.scores.description_seo = {
    score: Math.min(descScore, 10), max: 10,
    keywords_found: matchedKeywords,
    notes: descNotes,
  };

  // === 2. Naming Analysis ===
  let nameScore = 5;
  const nameNotes: string[] = [];
  
  if (nameLower.includes("_")) {
    nameNotes.push("Good: using snake_case naming convention (ACP standard).");
    nameScore += 2;
  }
  if (nameLower.length < 5) {
    nameNotes.push("Name is very short. More descriptive names improve search matching.");
    nameScore -= 2;
  } else if (nameLower.length > 30) {
    nameNotes.push("Name is quite long. Keep under 30 chars for readability.");
    nameScore -= 1;
  }
  const nameKeywords = BUTLER_KEYWORDS.filter((k) => nameLower.includes(k));
  if (nameKeywords.length > 0) {
    nameNotes.push(`Name contains search keywords: ${nameKeywords.join(", ")}.`);
    nameScore += 2;
  } else {
    nameNotes.push("Consider embedding a keyword in the name (e.g., 'token_analysis' instead of 'check_stuff').");
  }

  audit.value.scores.naming = {
    score: Math.max(0, Math.min(nameScore, 10)), max: 10, notes: nameNotes,
  };

  // === 3. Pricing Analysis ===
  let priceScore = 5;
  const priceNotes: string[] = [];
  
  if (price === 0) {
    priceNotes.push("Free offering. Good for initial traction, but consider adding a fee ($0.10-0.50) to signal quality.");
    priceScore = 6;
  } else if (price <= 0.5) {
    priceNotes.push(`Low price point ($${price}). Attractive for volume — good for building job count toward search ranking.`);
    priceScore = 8;
  } else if (price <= 2.0) {
    priceNotes.push(`Moderate price ($${price}). Balances revenue and accessibility.`);
    priceScore = 7;
  } else if (price <= 5.0) {
    priceNotes.push(`Higher price point ($${price}). Make sure description clearly justifies the value.`);
    priceScore = 5;
  } else {
    priceNotes.push(`Premium price ($${price}). May limit buyer volume which affects search ranking (job count is a ranking factor).`);
    priceScore = 3;
  }

  // Check against category norms
  for (const [category, range] of Object.entries(PRICE_RANGES)) {
    if (descLower.includes(category) || nameLower.includes(category)) {
      if (price < range.low) priceNotes.push(`For ${category}-type services, typical range is $${range.low}-$${range.high}. Your price is below average.`);
      else if (price > range.high) priceNotes.push(`For ${category}-type services, typical range is $${range.low}-$${range.high}. Your price is above average.`);
      break;
    }
  }

  audit.value.scores.pricing = { score: priceScore, max: 10, notes: priceNotes };

  // === 4. Schema Quality ===
  let schemaScore = 5;
  const schemaNotes: string[] = [];
  const props = schema?.properties;

  if (!props || Object.keys(props).length === 0) {
    schemaNotes.push("No requirement schema provided or schema is empty. A well-defined schema improves buyer experience and automation.");
    schemaScore = 3;
  } else {
    const propCount = Object.keys(props).length;
    schemaNotes.push(`${propCount} parameter(s) defined.`);
    if (propCount > 10) {
      schemaNotes.push("Too many parameters. Simplify to improve usability.");
      schemaScore -= 2;
    }

    // Check for descriptions on properties
    let withDesc = 0;
    let withType = 0;
    for (const [, val] of Object.entries(props) as [string, any][]) {
      if (val?.description) withDesc++;
      if (val?.type) withType++;
    }
    if (withDesc === propCount) {
      schemaNotes.push("All properties have descriptions — excellent for buyers.");
      schemaScore += 3;
    } else {
      schemaNotes.push(`${propCount - withDesc} properties lack descriptions. Add them to help buyers understand required inputs.`);
    }
    if (withType === propCount) {
      schemaNotes.push("All properties have type definitions.");
      schemaScore += 1;
    }

    // Required fields
    const required = schema?.required;
    if (required && required.length > 0) {
      schemaNotes.push(`${required.length} required field(s): ${required.join(", ")}.`);
    } else {
      schemaNotes.push("No required fields defined. Consider marking essential inputs as required.");
    }
  }

  audit.value.scores.schema_quality = {
    score: Math.max(0, Math.min(schemaScore, 10)), max: 10, notes: schemaNotes,
  };

  // === 5. Butler Search Ranking Factors (Advisory) ===
  const rankingAdvice: string[] = [
    "Butler ranking factors beyond your offering content:",
    "1. Success rate: Ensure your handler reliably completes jobs without errors.",
    "2. Unique buyer count: Attract diverse buyers, not just repeated self-tests.",
    "3. Job volume: Lower prices can increase volume and improve ranking.",
    "4. SLA compliance: Set a realistic SLA and always deliver within it.",
    "5. Online status: Keep your seller runtime running 24/7.",
    "6. Ratings: Deliver high-quality results to earn positive evaluations.",
  ];
  audit.value.ranking_advice = rankingAdvice;

  // === Overall Score ===
  const scores = Object.values(audit.value.scores) as any[];
  const total = scores.reduce((s: number, x: any) => s + (x.score || 0), 0);
  const maxTotal = scores.reduce((s: number, x: any) => s + (x.max || 0), 0);
  audit.value.overall_score = maxTotal > 0 ? Math.round((total / maxTotal) * 100) : 0;

  // === Top Recommendations ===
  const recs: string[] = [];
  if (descWords < 50) recs.push("Expand description to 50-150 words with relevant keywords.");
  if (matchedKeywords.length < 3) recs.push("Add more high-value search keywords to description.");
  if (!hasAction) recs.push("Use action verbs to describe what the buyer receives.");
  if (!hasValue) recs.push("Add a unique value proposition to differentiate from competitors.");
  if (price > 2.0) recs.push("Consider lowering price to increase job volume (ranking factor).");
  if (!props || Object.keys(props).length === 0) recs.push("Define a requirement schema with typed, described properties.");
  audit.value.recommendations = recs.length > 0 ? recs : ["Your offering looks well-optimized. Focus on completing jobs to build ranking signals."];

  return { deliverable: audit };
}
