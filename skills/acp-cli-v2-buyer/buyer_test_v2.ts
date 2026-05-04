#!/usr/bin/env npx tsx
// =============================================================================
// buyer_test_v2.ts — ACP v2 SDK Buyer Test Runner
// 1件発注テスト用。neo-test-buyer-v2 (0x11ab4...) から
// NeoAutonomous v2 (0x840cff90...) に vp_sentiment_scan ($0.01) を発注する。
//
// 仕様:
//  - chainId: 8453 (Base mainnet)
//  - evaluatorAddress = buyerAddress (self_evaluation)
//  - createJobByOfferingName で発注
//  - budget.set 受領で fund、submitted 受領で complete、completed で終了
// =============================================================================

// Polyfill: Node 18 does not expose crypto globally
import { webcrypto } from "node:crypto";
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto;
}

import { createAgentFromConfig } from "../acp-cli-v2/src/lib/agentFactory.js";
import { AssetToken } from "@virtuals-protocol/acp-node-v2";
import type { AcpAgent, JobSession, JobRoomEntry } from "@virtuals-protocol/acp-node-v2";

// ---------------------------------------------------------------------------
// 設定
// ---------------------------------------------------------------------------
const CHAIN_ID = 8453; // Base mainnet
const SELLER_ADDRESS = "0x840cff9032a4ce29845e05aed510f0ca4ea16cab"; // NeoAutonomous v2
const OFFERING_NAME = "vp_sentiment_scan"; // 最安 $0.01
const REQUIREMENT = {
  symbol: "VIRTUAL",
  include_headlines: false,
};

// ---------------------------------------------------------------------------
// ロガー
// ---------------------------------------------------------------------------
function log(level: "INFO" | "WARN" | "ERROR" | "DEBUG", msg: string): void {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [v2-buyer-test] [${level}] ${msg}`);
}

// ---------------------------------------------------------------------------
// メイン
// ---------------------------------------------------------------------------
async function main(): Promise<void> {
  log("INFO", "Starting buyer test runner");
  log("INFO", `Target seller: ${SELLER_ADDRESS}`);
  log("INFO", `Offering: ${OFFERING_NAME}`);
  log("INFO", `Chain ID: ${CHAIN_ID}`);

  // Buyer agent作成 (cwd の config.json を読む = activeWallet 0x11ab4...)
  const buyer: AcpAgent = await createAgentFromConfig();
  const buyerAddress = await buyer.getAddress();
  log("INFO", `Buyer address: ${buyerAddress}`);

  // 状態追跡
  let jobCompleted = false;
  let jobRejected = false;
  let lastJobId: string | undefined;

  // イベントハンドラ
  buyer.on("entry", async (session: JobSession, entry: JobRoomEntry) => {
    log("DEBUG", `entry kind=${entry.kind} jobId=${session.jobId} status=${session.status}`);

    if (entry.kind === "system") {
      const eventType = entry.event.type;
      log("INFO", `system event: ${eventType} (jobId=${session.jobId})`);

      switch (eventType) {
        case "budget.set": {
          // Sellerが予算を提示してきた → fund する
          log("INFO", `budget.set received, funding job ${session.jobId}...`);
          try {
            await session.fund(); // 提示額を満たす
            log("INFO", `funded job ${session.jobId}`);
          } catch (e: any) {
            log("ERROR", `fund failed: ${e.message}`);
            jobRejected = true;
          }
          break;
        }
        case "job.submitted": {
          log("INFO", `Seller submitted deliverable for job ${session.jobId}`);
          // self_evaluation: buyer = evaluator なので自分で complete を出す
          try {
            await session.complete("Test approval (self_evaluation)");
            log("INFO", `completed job ${session.jobId}`);
          } catch (e: any) {
            log("ERROR", `complete failed: ${e.message}`);
            jobRejected = true;
          }
          break;
        }
        case "job.completed": {
          log("INFO", `✅ Job ${session.jobId} COMPLETED`);
          jobCompleted = true;
          break;
        }
        case "job.rejected": {
          log("WARN", `⚠️ Job ${session.jobId} REJECTED`);
          jobRejected = true;
          break;
        }
      }
    }
  });

  // SSE接続開始
  await buyer.start();
  log("INFO", "Buyer started, listening on SSE");

  // 1件発注
  log("INFO", `Creating job: offering=${OFFERING_NAME} -> seller=${SELLER_ADDRESS}`);
  let jobId: string;
  try {
    jobId = await buyer.createJobByOfferingName(
      CHAIN_ID,
      OFFERING_NAME,
      SELLER_ADDRESS as `0x${string}`,
      REQUIREMENT,
      { evaluatorAddress: buyerAddress } // self_evaluation
    );
    lastJobId = jobId;
    log("INFO", `✅ Job created: ${jobId}`);
  } catch (e: any) {
    log("ERROR", `createJobByOfferingName failed: ${e.message}`);
    log("ERROR", `stack: ${e.stack}`);
    await buyer.stop();
    process.exit(1);
  }

  // 完了待ち (最大10分)
  const maxWaitMs = 10 * 60 * 1000;
  const startedAt = Date.now();
  while (!jobCompleted && !jobRejected) {
    if (Date.now() - startedAt > maxWaitMs) {
      log("WARN", `Timeout waiting for job ${lastJobId}`);
      break;
    }
    await new Promise((r) => setTimeout(r, 5000));
    log("DEBUG", `Waiting... elapsed=${Math.floor((Date.now() - startedAt) / 1000)}s`);
  }

  log("INFO", "Stopping buyer");
  await buyer.stop();

  if (jobCompleted) {
    log("INFO", "🎉 Test PASSED: job completed end-to-end");
    process.exit(0);
  } else if (jobRejected) {
    log("WARN", "Test result: job rejected (expected if seller is in DRY_RUN mode)");
    process.exit(2);
  } else {
    log("WARN", "Test result: timeout");
    process.exit(3);
  }
}

main().catch((e: any) => {
  console.error("[v2-buyer-test] Fatal:", e);
  process.exit(1);
});
