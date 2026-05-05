#!/usr/bin/env npx tsx
// =============================================================================
// buyer_batch_v2.ts — ACP v2 SDK Buyer Batch Runner (v2: 並行処理対応)
// 9件の vp_sentiment_scan ($0.01) を逐次発注する。
// 既に Job 6333/6340 で2件成功済のため、合計10件で Graduation条件達成を目指す。
//
// 修正点 (前バージョンからの変更):
//  - イベントフィルタを撤廃: 全ジョブのイベントを処理する
//  - jobStates: Map<jobId, JobState> で複数ジョブを並行追跡
//  - 救出ジョブ (起動時に再配信される未完了ジョブ) も自動的にカウント
//  - 「次の発注に進む条件」は 直前発注ジョブの完走 or 5分タイムアウト
// =============================================================================

import { webcrypto } from "node:crypto";
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto;
}

import { createAgentFromConfig } from "../acp-cli-v2/src/lib/agentFactory.js";
import type { AcpAgent, JobSession, JobRoomEntry } from "@virtuals-protocol/acp-node-v2";

// ---------------------------------------------------------------------------
// 設定
// ---------------------------------------------------------------------------
const CHAIN_ID = 8453;
const SELLER_ADDRESS = "0x840cff9032a4ce29845e05aed510f0ca4ea16cab";
const OFFERING_NAME = "vp_sentiment_scan";
const REQUIREMENT = { symbol: "VIRTUAL", include_headlines: false };
const TOTAL_NEW_JOBS = 9;
const INTER_JOB_SLEEP_MS = 30 * 1000;
const PER_JOB_TIMEOUT_MS = 5 * 60 * 1000;

// ---------------------------------------------------------------------------
// ロガー
// ---------------------------------------------------------------------------
function log(level: "INFO" | "WARN" | "ERROR" | "DEBUG", msg: string): void {
  const ts = new Date().toISOString();
  console.log(`[${ts}] [v2-buyer-batch] [${level}] ${msg}`);
}

// ---------------------------------------------------------------------------
// ジョブ状態管理
// ---------------------------------------------------------------------------
interface JobState {
  jobId: string;
  source: "new" | "rescued";
  status: "pending" | "funded" | "submitted" | "completed" | "rejected";
  createdAt: number;
}

const jobStates: Map<string, JobState> = new Map();

const STATUS_ORDER: Record<JobState["status"], number> = {
  pending: 0,
  funded: 1,
  submitted: 2,
  completed: 3,
  rejected: 3,
};

function isTerminal(s: JobState["status"]): boolean {
  return s === "completed" || s === "rejected";
}

function setJobState(jobId: string, partial: Partial<JobState> & { source?: JobState["source"] }): JobState {
  const existing = jobStates.get(jobId);
  if (existing) {
    // status は前進方向のみ更新 (terminal状態は変更不可)
    if (partial.status !== undefined) {
      if (isTerminal(existing.status)) {
        // 既にcompletedまたはrejectedなら何もしない
        delete partial.status;
      } else if (STATUS_ORDER[partial.status] < STATUS_ORDER[existing.status]) {
        // 後退方向の更新は無視
        delete partial.status;
      }
    }
    Object.assign(existing, partial);
    return existing;
  }
  const fresh: JobState = {
    jobId,
    source: partial.source ?? "rescued",
    status: partial.status ?? "pending",
    createdAt: Date.now(),
  };
  jobStates.set(jobId, fresh);
  return fresh;
}

// ---------------------------------------------------------------------------
// メイン
// ---------------------------------------------------------------------------
async function main(): Promise<void> {
  log("INFO", "=== ACP v2 Batch Buyer (parallel-safe) starting ===");
  log("INFO", `New jobs to send: ${TOTAL_NEW_JOBS}`);
  log("INFO", `Target seller: ${SELLER_ADDRESS}`);
  log("INFO", `Offering: ${OFFERING_NAME} ($0.01 each)`);

  const buyer: AcpAgent = await createAgentFromConfig();
  const buyerAddress = (await buyer.getAddress()) as `0x${string}`;
  log("INFO", `Buyer address: ${buyerAddress}`);

  // 単一の entry ハンドラ (全ジョブのイベントを処理)
  buyer.on("entry", async (session: JobSession, entry: JobRoomEntry) => {
    if (entry.kind !== "system") return;
    const jobId = String(session.jobId);
    const eventType = entry.event.type;

    // 状態更新 (新規jobIdなら "rescued" 扱いで初期化)
    const state = setJobState(jobId, {});
    log("DEBUG", `event=${eventType} jobId=${jobId} source=${state.source} status=${state.status}`);

    switch (eventType) {
      case "budget.set": {
        log("INFO", `[${jobId}] budget.set received, funding...`);
        try {
          await session.fund();
          setJobState(jobId, { status: "funded" });
          log("INFO", `[${jobId}] funded`);
        } catch (e: any) {
          log("ERROR", `[${jobId}] fund failed: ${e.message}`);
          setJobState(jobId, { status: "rejected" });
        }
        break;
      }
      case "job.submitted": {
        log("INFO", `[${jobId}] seller submitted, completing...`);
        try {
          await session.complete("Batch approval (self_evaluation)");
          setJobState(jobId, { status: "submitted" });
          log("INFO", `[${jobId}] complete sent`);
        } catch (e: any) {
          log("ERROR", `[${jobId}] complete failed: ${e.message}`);
          setJobState(jobId, { status: "rejected" });
        }
        break;
      }
      case "job.completed": {
        log("INFO", `[${jobId}] ✅ COMPLETED (source=${state.source})`);
        setJobState(jobId, { status: "completed" });
        break;
      }
      case "job.rejected": {
        log("WARN", `[${jobId}] ⚠️ REJECTED`);
        setJobState(jobId, { status: "rejected" });
        break;
      }
    }
  });

  await buyer.start();
  log("INFO", "Buyer started (SSE), waiting 5s for rescue events...");
  await new Promise((r) => setTimeout(r, 5000)); // 救出イベント受信猶予

  log("INFO", `Initial rescued jobs: ${jobStates.size}`);
  for (const [jid, st] of jobStates) {
    log("INFO", `  rescued: ${jid} status=${st.status}`);
  }

  // 新規発注ループ
  const newJobIds: string[] = [];
  for (let i = 1; i <= TOTAL_NEW_JOBS; i++) {
    log("INFO", `=== New Job ${i}/${TOTAL_NEW_JOBS} creating ===`);
    let jobId: string;
    try {
      jobId = await buyer.createJobByOfferingName(
        CHAIN_ID,
        OFFERING_NAME,
        SELLER_ADDRESS as `0x${string}`,
        REQUIREMENT,
        { evaluatorAddress: buyerAddress }
      );
      log("INFO", `✅ Created: ${jobId}`);
      setJobState(jobId, { source: "new", status: "pending" });
      newJobIds.push(jobId);
    } catch (e: any) {
      log("ERROR", `createJob failed: ${e.message}`);
      // 失敗してもスリープ後に次を試す
      await new Promise((r) => setTimeout(r, INTER_JOB_SLEEP_MS));
      continue;
    }

    // 直前発注ジョブの完走を待つ (or タイムアウト)
    const startedAt = Date.now();
    let pollCount = 0;
    while (true) {
      const st = jobStates.get(jobId);
      pollCount++;
      if (pollCount % 3 === 1) {
        log("DEBUG", `[${jobId}] polling status=${st?.status ?? "missing"} elapsed=${Math.floor((Date.now() - startedAt) / 1000)}s`);
      }
      if (st?.status === "completed" || st?.status === "rejected") {
        log("INFO", `[${jobId}] loop exit: status=${st.status}`);
        break;
      }
      if (Date.now() - startedAt > PER_JOB_TIMEOUT_MS) {
        log("WARN", `[${jobId}] timeout waiting (final status=${st?.status ?? "missing"})`);
        break;
      }
      await new Promise((r) => setTimeout(r, 3000));
    }

    // 進捗ログ
    const completed = Array.from(jobStates.values()).filter((s) => s.status === "completed").length;
    const rescuedCompleted = Array.from(jobStates.values()).filter(
      (s) => s.source === "rescued" && s.status === "completed"
    ).length;
    log("INFO", `--- Progress: total completed=${completed} (rescued=${rescuedCompleted}, new=${completed - rescuedCompleted}) ---`);

    if (i < TOTAL_NEW_JOBS) {
      log("INFO", `Sleeping ${INTER_JOB_SLEEP_MS / 1000}s before next...`);
      await new Promise((r) => setTimeout(r, INTER_JOB_SLEEP_MS));
    }
  }

  // 残ジョブの完走を最大2分待機
  log("INFO", "Waiting up to 2min for remaining jobs to settle...");
  const finalDeadline = Date.now() + 120 * 1000;
  while (Date.now() < finalDeadline) {
    const pending = Array.from(jobStates.values()).filter(
      (s) => s.status !== "completed" && s.status !== "rejected"
    );
    if (pending.length === 0) break;
    await new Promise((r) => setTimeout(r, 5000));
    log("DEBUG", `pending=${pending.length}`);
  }

  await buyer.stop();
  log("INFO", "Buyer stopped");

  // === サマリー ===
  log("INFO", "=== SUMMARY ===");
  const all = Array.from(jobStates.values()).sort((a, b) => Number(a.jobId) - Number(b.jobId));
  for (const s of all) {
    log("INFO", `  Job ${s.jobId}: ${s.status} (source=${s.source})`);
  }

  // 連続成功数の計算 (jobId 順、completed のみカウント)
  let maxStreak = 0;
  let curStreak = 0;
  for (const s of all) {
    if (s.status === "completed") {
      curStreak++;
      if (curStreak > maxStreak) maxStreak = curStreak;
    } else {
      curStreak = 0;
    }
  }
  const totalCompleted = all.filter((s) => s.status === "completed").length;
  log("INFO", `Total completed in this run: ${totalCompleted}`);
  log("INFO", `Max consecutive streak in this run: ${maxStreak}`);
  log("INFO", `(Plus prior successful: Job 6333 from previous session)`);

  process.exit(0);
}

main().catch((e: any) => {
  console.error("[v2-buyer-batch] Fatal:", e);
  process.exit(1);
});
