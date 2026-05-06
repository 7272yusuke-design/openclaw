#!/usr/bin/env npx tsx
// Polyfill: Node 18 does not expose crypto globally
import { webcrypto } from "node:crypto";
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto;
}
// =============================================================================
// Native ACP SDK Seller runtime
// Uses @virtuals-protocol/acp-node directly (not OpenClaw CLI wrapper)
// =============================================================================

import AcpClientDefault, {
  AcpContractClientV2,
  AcpJobPhases,
} from "@virtuals-protocol/acp-node";
const AcpClient = AcpClientDefault.default || AcpClientDefault;
import type { AcpJob, AcpMemo } from "@virtuals-protocol/acp-node";
import { loadOffering, listOfferings } from "./offerings.js";
import type { ExecuteJobResult } from "./offeringTypes.js";
import dotenv from "dotenv";
import * as path from "path";
import { fileURLToPath } from "url";

// Load .env from workspace root
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const workspaceRoot = path.resolve(__dirname, "..", "..", "..", "..", "..");
dotenv.config({ path: path.join(workspaceRoot, ".env") });

// Also load from ACP skill root
dotenv.config({ path: path.join(__dirname, "..", "..", "..", ".env") });

const PRIVATE_KEY = process.env.WHITELISTED_WALLET_PRIVATE_KEY!;
const ENTITY_KEY_ID = parseInt(process.env.SESSION_ENTITY_KEY_ID!, 10);
const AGENT_WALLET = process.env.NATIVE_AGENT_WALLET_ADDRESS!;

// -- Discord notification --

async function notifyDiscord(message: string): Promise<void> {
  try {
    const url = process.env.DISCORD_LOG_WEBHOOK || process.env.DISCORD_WEBHOOK_URL;
    if (url) {
      await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content: message }),
      });
    }
  } catch (e) {
    console.error("[native-seller] Discord notify error:", e);
  }
}

// -- Resolve offering name from job memos --

function resolveOfferingName(job: any): string | undefined {
  // Try job.name first (native SDK)
  if (job.name) return job.name;
  // Fallback: parse from NEGOTIATION memo content
  for (const m of (job.memos || [])) {
    if (m.nextPhase === AcpJobPhases.NEGOTIATION || m.nextPhase === 1) {
      try {
        const parsed = JSON.parse(typeof m.content === 'string' ? m.content : JSON.stringify(m.content));
        if (parsed.name) return parsed.name;
      } catch {}
    }
  }
  // Fallback: check context
  if (job.context?.name) return job.context.name;
  // Fallback: check memo content for _offeringName field
  for (const m of (job.memos || [])) {
    try {
      const parsed = JSON.parse(typeof m.content === 'string' ? m.content : JSON.stringify(m.content));
      if (parsed._offeringName) return parsed._offeringName;
    } catch {}
  }
  return undefined;
}

function resolveRequirements(job: any): Record<string, any> {
  // Try job.requirement first (native SDK)
  if (typeof job.requirement === 'object' && job.requirement !== null) return job.requirement;
  // Fallback: parse from NEGOTIATION memo - content IS the requirements
  for (const m of (job.memos || [])) {
    if (m.nextPhase === AcpJobPhases.NEGOTIATION || m.nextPhase === 1) {
      try {
        const parsed = JSON.parse(typeof m.content === 'string' ? m.content : JSON.stringify(m.content));
        if (parsed.requirement) return parsed.requirement;
        // Content itself is the requirements object
        if (typeof parsed === 'object' && parsed !== null) return parsed;
      } catch {}
    }
  }
  return {};
}

// -- Job handling --

async function handleNewTask(job: AcpJob, memoToSign?: AcpMemo): Promise<void> {
  const phase = AcpJobPhases[job.phase] ?? String(job.phase);
  console.log(`\n${"=".repeat(60)}`);
  console.log(`[native-seller] Job ${job.id} | phase=${phase} | name=${job.name}`);
  console.log(`  client=${job.clientAddress}  price=${job.price}`);
  console.log(`${"=".repeat(60)}`);

  await notifyDiscord(
    `🔔 **ACP Job (Native)**\nOffering: ${job.name || "unknown"}\nJob ID: ${job.id}\nClient: ${job.clientAddress}\nPrice: ${job.price}\nPhase: ${phase}`
  );

  // --- REQUEST phase: accept or reject ---
  if (job.phase === AcpJobPhases.REQUEST && memoToSign) {
    const offeringName = resolveOfferingName(job);
    const requirements = resolveRequirements(job);

    if (!offeringName) {
      console.log(`[native-seller] No offering name — rejecting job ${job.id}`);
      await job.reject("Invalid offering name");
      return;
    }

    try {
      const { config, handlers } = await loadOffering(offeringName);

      // Validate requirements if handler provides validation
      if (handlers.validateRequirements) {
        const validationResult = handlers.validateRequirements(requirements);
        let isValid: boolean;
        let reason: string | undefined;

        if (typeof validationResult === "boolean") {
          isValid = validationResult;
          reason = isValid ? undefined : "Validation failed";
        } else {
          isValid = validationResult.valid;
          reason = validationResult.reason;
        }

        if (!isValid) {
          const rejectionReason = reason || "Validation failed";
          console.log(
            `[native-seller] Validation failed for "${offeringName}": ${rejectionReason}`
          );
          await job.reject(rejectionReason);
          return;
        }
      }

      console.log(`[native-seller] Accepting job ${job.id} for "${offeringName}"`);
      await job.accept("Job accepted — processing will begin on payment confirmation");

      // Move job from NEGOTIATION to TRANSACTION by creating payment requirement
      console.log(`[native-seller] Requesting payment for job ${job.id}...`);
      await job.createRequirement("Service request accepted. Payment required to proceed.");
      console.log(`[native-seller] Payment requested for job ${job.id} ✅`);
    } catch (err) {
      console.error(`[native-seller] Error in REQUEST for job ${job.id}:`, err);
      try {
        await job.reject("Internal processing error");
      } catch (rejectErr) {
        console.error(`[native-seller] Failed to reject job ${job.id}:`, rejectErr);
      }
    }
    return;
  }

  // --- TRANSACTION phase: execute and deliver ---
  if (job.phase === AcpJobPhases.TRANSACTION) {
    const offeringName = resolveOfferingName(job);
    const requirements = resolveRequirements(job);

    if (!offeringName) {
      console.log(`[native-seller] No offering in TRANSACTION phase — skipping job ${job.id}`);
      return;
    }

    try {
      const { handlers } = await loadOffering(offeringName);
      console.log(
        `[native-seller] Executing "${offeringName}" for job ${job.id} (TRANSACTION)...`
      );
      const result: ExecuteJobResult = await handlers.executeJob(requirements);

      console.log(`[native-seller] Delivering job ${job.id}...`);
      await job.deliver(result.deliverable);
      console.log(`[native-seller] Job ${job.id} — delivered ✅`);

      await notifyDiscord(`✅ **Job ${job.id} Delivered**\nOffering: ${offeringName}`);
    } catch (err) {
      console.error(`[native-seller] Error delivering job ${job.id}:`, err);
      await notifyDiscord(`❌ **Job ${job.id} Failed**\nOffering: ${offeringName}\nError: ${err}`);
    }
    return;
  }

  console.log(`[native-seller] Job ${job.id} in phase ${phase} — no action needed`);
}

// -- Main --

async function main(): Promise<void> {
  // Validate environment
  if (!PRIVATE_KEY || !AGENT_WALLET || isNaN(ENTITY_KEY_ID)) {
    console.error(
      "[native-seller] Missing required env vars:\n" +
        "  WHITELISTED_WALLET_PRIVATE_KEY\n" +
        "  NATIVE_AGENT_WALLET_ADDRESS\n" +
        "  SESSION_ENTITY_KEY_ID"
    );
    process.exit(1);
  }

  console.log("[native-seller] Initializing Native ACP SDK Seller...");
  console.log(`  Agent wallet:  ${AGENT_WALLET}`);
  console.log(`  Dev wallet:    ${process.env.WHITELISTED_WALLET_ADDRESS || "?"}`);
  console.log(`  Entity Key ID: ${ENTITY_KEY_ID}`);

  // Build contract client with native SDK
  const contractClient = await AcpContractClientV2.build(
    PRIVATE_KEY as `0x${string}`,
    ENTITY_KEY_ID,
    AGENT_WALLET as `0x${string}`
  );

  // Create ACP client with WebSocket callbacks
  const acpClient = new AcpClient({
    acpContractClient: contractClient,
    onNewTask: (job: AcpJob, memoToSign?: AcpMemo) => {
      handleNewTask(job, memoToSign).catch((err) =>
        console.error("[native-seller] Unhandled error in handleNewTask:", err)
      );
    },
    onEvaluate: (job: AcpJob) => {
      console.log(
        `[native-seller] onEvaluate for job ${job.id} — handled by protocol`
      );
    },
  });

  const offerings = listOfferings();
  console.log(
    `[native-seller] Available offerings: ${
      offerings.length > 0 ? offerings.join(", ") : "(none)"
    }`
  );
  console.log("[native-seller] Native seller runtime is running. Waiting for jobs...\n");

  await notifyDiscord("🟢 **Neo Native Seller Started**\nWaiting for ACP jobs...");

  // Keep alive
  process.on("SIGINT", () => {
    console.log("[native-seller] SIGINT — shutting down");
    process.exit(0);
  });
  process.on("SIGTERM", () => {
    console.log("[native-seller] SIGTERM — shutting down");
    process.exit(0);
  });
}

main().catch((err) => {
  console.error("[native-seller] Fatal error:", err);
  process.exit(1);
});
