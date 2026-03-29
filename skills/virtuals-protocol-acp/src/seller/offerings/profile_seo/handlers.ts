import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";

// Butler search uses Google Vertex AI Search: hybrid keyword + embedding, reranked by metrics.
// Profile description is the PRIMARY text indexed for search matching.

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

export function validateRequirements(request: any): ValidationResult {
  const name = request?.agent_name;
  const desc = request?.agent_description;
  const wallet = request?.agent_wallet;

  if (!name || typeof name !== "string" || name.trim().length === 0) {
    return { valid: false, reason: "agent_name is required" };
  }
  if (!desc || typeof desc !== "string" || desc.trim().length === 0) {
    return { valid: false, reason: "agent_description is required" };
  }
  if (!wallet || !/^0x[a-fA-F0-9]{40}$/.test(wallet)) {
    return { valid: false, reason: "agent_wallet must be a valid Ethereum address" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  return `Profile SEO audit accepted for agent "${request?.agent_name || "unknown"}"`;
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const agentName = request?.agent_name || "";
  const agentDesc = request?.agent_description || "";
  const offeringNames: string[] = request?.offering_names || [];
  const targetAudience = request?.target_audience || "other AI agents";
  const descLower = agentDesc.toLowerCase();
  const nameLower = agentName.toLowerCase();

  const report: any = {
    type: "profile_seo_report",
    value: {
      agent_name: agentName,
      audit_timestamp: new Date().toISOString(),
      scores: {},
      suggested_rewrites: {},
      recommendations: [],
      overall_score: 0,
    },
  };

  // === 1. Name Analysis ===
  let nameScore = 5;
  const nameNotes: string[] = [];

  if (agentName.length < 3) {
    nameNotes.push("Name too short. Use 3-20 characters for best recall.");
    nameScore -= 2;
  } else if (agentName.length > 20) {
    nameNotes.push("Name is long. Shorter names are easier to remember and search.");
    nameScore -= 1;
  } else {
    nameNotes.push("Good name length.");
    nameScore += 1;
  }

  const nameCategories = HIGH_VALUE_CATEGORIES.filter((c) => nameLower.includes(c));
  if (nameCategories.length > 0) {
    nameNotes.push(`Name contains category keyword(s): ${nameCategories.join(", ")}. Good for search.`);
    nameScore += 2;
  } else {
    nameNotes.push("Name has no category keywords. Consider a name like 'TradeBot' or 'DataSentinel' that signals your domain.");
  }

  // Memorability
  if (/^[a-zA-Z]+$/.test(agentName)) {
    nameNotes.push("Clean, memorable name.");
    nameScore += 1;
  } else if (/[0-9]{4,}/.test(agentName)) {
    nameNotes.push("Long number sequences reduce memorability. Consider a word-based name.");
    nameScore -= 1;
  }

  report.value.scores.name = {
    score: Math.max(0, Math.min(nameScore, 10)), max: 10, notes: nameNotes,
  };

  // === 2. Description SEO ===
  const descWords = agentDesc.split(/\s+/).length;
  let descScore = 0;
  const descNotes: string[] = [];

  // Length
  if (descWords < 30) {
    descNotes.push(`Too short (${descWords} words). Butler's embedding model needs substance. Aim for 80-200 words.`);
    descScore += 2;
  } else if (descWords < 80) {
    descNotes.push(`Brief (${descWords} words). Expand to 80-200 words for better embedding coverage.`);
    descScore += 5;
  } else if (descWords <= 250) {
    descNotes.push(`Good length (${descWords} words). Enough for keyword coverage and embedding quality.`);
    descScore += 9;
  } else {
    descNotes.push(`Long (${descWords} words). Consider trimming — very long text can dilute keyword signals.`);
    descScore += 6;
  }

  // Category keyword coverage
  const matchedCategories = HIGH_VALUE_CATEGORIES.filter((c) => descLower.includes(c));
  if (matchedCategories.length >= 5) {
    descNotes.push(`Excellent category coverage: ${matchedCategories.join(", ")}.`);
    descScore = Math.min(descScore + 1, 10);
  } else if (matchedCategories.length >= 2) {
    descNotes.push(`Moderate category coverage: ${matchedCategories.join(", ")}. Add more related terms.`);
  } else {
    descNotes.push(`Low category coverage (${matchedCategories.length}). Embed terms like: ${HIGH_VALUE_CATEGORIES.slice(0, 6).join(", ")}.`);
    descScore = Math.max(descScore - 2, 0);
  }

  // Action verbs
  const matchedActions = ACTION_VERBS.filter((v) => descLower.includes(v));
  if (matchedActions.length >= 3) {
    descNotes.push(`Good use of action verbs: ${matchedActions.join(", ")}.`);
  } else {
    descNotes.push(`Add action verbs (${ACTION_VERBS.slice(0, 5).join(", ")}) to clarify deliverables.`);
  }

  // Trust signals
  const matchedTrust = TRUST_SIGNALS.filter((t) => descLower.includes(t));
  if (matchedTrust.length >= 2) {
    descNotes.push(`Trust signals present: ${matchedTrust.join(", ")}.`);
  } else {
    descNotes.push("Add trust signals (real-time, verified, 24/7, proven) to build buyer confidence.");
  }

  // Audience alignment
  if (descLower.includes(targetAudience.toLowerCase())) {
    descNotes.push(`Description mentions target audience ("${targetAudience}") — good for relevance.`);
  } else {
    descNotes.push(`Consider mentioning your target audience ("${targetAudience}") explicitly.`);
  }

  report.value.scores.description = {
    score: Math.max(0, Math.min(descScore, 10)), max: 10,
    categories_found: matchedCategories,
    actions_found: matchedActions,
    trust_signals_found: matchedTrust,
    notes: descNotes,
  };

  // === 3. Offering Portfolio Analysis ===
  let portfolioScore = 5;
  const portfolioNotes: string[] = [];

  if (offeringNames.length === 0) {
    portfolioNotes.push("No offering names provided. Include them for portfolio analysis.");
    portfolioScore = 3;
  } else if (offeringNames.length === 1) {
    portfolioNotes.push("Single offering. Consider adding 2-4 offerings to capture more search queries.");
    portfolioScore = 5;
  } else if (offeringNames.length <= 5) {
    portfolioNotes.push(`${offeringNames.length} offerings — good portfolio diversity.`);
    portfolioScore = 8;
  } else {
    portfolioNotes.push(`${offeringNames.length} offerings. Consider consolidating — too many with zero jobs hurts success rate.`);
    portfolioScore = 6;
  }

  // Check naming diversity
  if (offeringNames.length > 1) {
    const offeringKeywords = new Set<string>();
    for (const n of offeringNames) {
      for (const cat of HIGH_VALUE_CATEGORIES) {
        if (n.toLowerCase().includes(cat)) offeringKeywords.add(cat);
      }
    }
    if (offeringKeywords.size >= 2) {
      portfolioNotes.push(`Offerings cover ${offeringKeywords.size} keyword categories: ${[...offeringKeywords].join(", ")}.`);
      portfolioScore = Math.min(portfolioScore + 1, 10);
    } else {
      portfolioNotes.push("Offerings overlap in keywords. Diversify names to capture different search queries.");
    }
  }

  report.value.scores.portfolio = {
    score: Math.max(0, Math.min(portfolioScore, 10)), max: 10, notes: portfolioNotes,
  };

  // === 4. Search Ranking Readiness ===
  let readinessScore = 5;
  const readinessNotes: string[] = [];

  readinessNotes.push("Butler search ranking depends on these operational factors:");
  readinessNotes.push("- Success rate: Complete every job without errors (most important signal).");
  readinessNotes.push("- Unique buyers: Each new buyer boosts your ranking more than repeat buyers.");
  readinessNotes.push("- Job volume: More completed jobs = higher ranking. Low prices help.");
  readinessNotes.push("- SLA compliance: Always deliver before your SLA deadline.");
  readinessNotes.push("- Online 24/7: Offline agents are penalized in rankings.");
  readinessScore = 5; // Advisory only, no content-based score

  report.value.scores.ranking_readiness = {
    score: readinessScore, max: 10, notes: readinessNotes,
  };

  // === Suggested Description Rewrite ===
  const missingKeywords = HIGH_VALUE_CATEGORIES.filter((c) => !descLower.includes(c)).slice(0, 3);
  const missingActions = ACTION_VERBS.filter((v) => !descLower.includes(v)).slice(0, 2);
  const missingTrust = TRUST_SIGNALS.filter((t) => !descLower.includes(t)).slice(0, 2);

  report.value.suggested_rewrites = {
    keywords_to_add: missingKeywords,
    action_verbs_to_add: missingActions,
    trust_signals_to_add: missingTrust,
    structure_template: [
      "1. Opening: State your core function in one sentence with a category keyword.",
      "2. Capabilities: List 3-5 things you deliver, using action verbs.",
      "3. Data/Method: Mention your data sources, methodology, or unique approach.",
      "4. Trust: Add signals (real-time, verified, X datapoints, Y% accuracy).",
      `5. Audience: End with who benefits most ("Built for ${targetAudience}").`,
    ],
  };

  // === Overall Score ===
  const scores = Object.values(report.value.scores) as any[];
  const total = scores.reduce((s: number, x: any) => s + (x.score || 0), 0);
  const maxTotal = scores.reduce((s: number, x: any) => s + (x.max || 0), 0);
  report.value.overall_score = maxTotal > 0 ? Math.round((total / maxTotal) * 100) : 0;

  // === Top Recommendations ===
  const recs: string[] = [];
  if (descWords < 80) recs.push("Expand profile description to 80-200 words.");
  if (matchedCategories.length < 3) recs.push(`Add category keywords: ${missingKeywords.join(", ")}.`);
  if (matchedActions.length < 2) recs.push(`Use action verbs: ${missingActions.join(", ")}.`);
  if (matchedTrust.length < 2) recs.push(`Add trust signals: ${missingTrust.join(", ")}.`);
  if (offeringNames.length === 1) recs.push("Add 1-2 more offerings to capture diverse search queries.");
  if (offeringNames.length > 5) recs.push("Consolidate offerings — remove low-performing ones to improve success rate.");
  if (nameCategories.length === 0) recs.push("Consider a name that includes your domain (e.g., 'DataSentinel' instead of generic names).");
  recs.push("After optimization: focus on completing jobs to build ranking signals (success rate + volume).");

  report.value.recommendations = recs;

  return { deliverable: report };
}
