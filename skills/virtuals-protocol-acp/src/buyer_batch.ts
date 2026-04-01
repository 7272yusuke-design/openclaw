import { webcrypto } from "node:crypto";
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto;
}
import AcpClientDefault, { AcpContractClientV2, AcpJobPhases, Fare, FareAmount } from "@virtuals-protocol/acp-node";
const AcpClient = (AcpClientDefault as any).default || AcpClientDefault;
import dotenv from "dotenv";
dotenv.config({ path: "/docker/openclaw-taan/data/.openclaw/workspace/.env" });

const SELLER_WALLET = process.env.NATIVE_AGENT_WALLET_ADDRESS!;
const USDC_BASE = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913";
const EVALUATOR = "0x0000000000000000000000000000000000000000";  // skip evaluation

const JOBS = [
  { offering: "offering_audit", reqs: { target_wallet: SELLER_WALLET, offering_name: "profile_seo", offering_description: "Audit test 1", offering_price: 0.3 }},
  { offering: "profile_seo", reqs: { agent_name: "NeoAutonomous", agent_description: "VP trading agent", agent_wallet: SELLER_WALLET }},
  { offering: "offering_audit", reqs: { target_wallet: SELLER_WALLET, offering_name: "offering_audit", offering_description: "Audit test 2", offering_price: 0.3 }},
  { offering: "profile_seo", reqs: { agent_name: "NeoAutonomous", agent_description: "VP trading agent with backtesting", agent_wallet: SELLER_WALLET }},
  { offering: "offering_audit", reqs: { target_wallet: SELLER_WALLET, offering_name: "profile_seo", offering_description: "Audit test 3", offering_price: 0.3 }},
  { offering: "profile_seo", reqs: { agent_name: "NeoAutonomous", agent_description: "Autonomous AI agent", agent_wallet: SELLER_WALLET }},
  { offering: "offering_audit", reqs: { target_wallet: SELLER_WALLET, offering_name: "offering_audit", offering_description: "Audit test 4", offering_price: 0.3 }},
  { offering: "profile_seo", reqs: { agent_name: "NeoAutonomous", agent_description: "VP ecosystem specialist", agent_wallet: SELLER_WALLET }},
  { offering: "offering_audit", reqs: { target_wallet: SELLER_WALLET, offering_name: "profile_seo", offering_description: "Audit test 5", offering_price: 0.3 }},
];

async function main() {
  console.log(`[batch] Starting ${JOBS.length} jobs...`);
  const contractClient = await AcpContractClientV2.build(
    process.env.BUYER_WHITELISTED_WALLET_PRIVATE_KEY! as `0x${string}`,
    parseInt(process.env.BUYER_SESSION_ENTITY_KEY_ID!, 10),
    process.env.BUYER_AGENT_WALLET_ADDRESS! as `0x${string}`
  );

  const completedJobs: number[] = [];

  const acpClient = new AcpClient({
    acpContractClient: contractClient,
    onNewTask: (job: any) => {
      if (job.phase === AcpJobPhases.NEGOTIATION) {
        console.log(`[batch] Auto-paying job ${job.id}...`);
        job.payAndAcceptRequirement("Payment confirmed").then(() => {
          console.log(`[batch] Paid job ${job.id} ✅`);
        }).catch((e: any) => console.error(`[batch] Pay error job ${job.id}:`, e));
      }
      if (job.phase === AcpJobPhases.COMPLETED) {
        console.log(`[batch] Job ${job.id} COMPLETED ✅`);
        completedJobs.push(job.id);
      }
    },
  });

  const usdcFare = await Fare.fromContractAddress(USDC_BASE as `0x${string}`);

  for (let i = 0; i < JOBS.length; i++) {
    const j = JOBS[i];
    const reqs = { _offeringName: j.offering, ...j.reqs };
    const fareAmount = new FareAmount(0.3, usdcFare);

    console.log(`\n[batch] === Job ${i + 1}/${JOBS.length}: ${j.offering} ===`);
    try {
      const jobId = await acpClient.initiateJob(
        SELLER_WALLET as `0x${string}`,
        JSON.stringify(reqs),
        fareAmount,
        EVALUATOR as `0x${string}`,
        new Date(Date.now() + 30 * 60 * 1000),
        j.offering
      );
      console.log(`[batch] Created job ${jobId}`);

      // Wait for completion (max 60s per job)
      for (let t = 0; t < 12; t++) {
        await new Promise(r => setTimeout(r, 5000));
        const status = await acpClient.getJobById(jobId);
        if (status) {
          const phase = AcpJobPhases[status.phase];
          if (status.phase === AcpJobPhases.COMPLETED) {
            console.log(`[batch] Job ${jobId} confirmed COMPLETED`);
            break;
          }
          if (status.phase === AcpJobPhases.REJECTED || status.phase === AcpJobPhases.EXPIRED) {
            console.log(`[batch] Job ${jobId} ${phase} — skipping`);
            break;
          }
        }
      }
    } catch (e) {
      console.error(`[batch] Error on job ${i + 1}:`, e);
    }
    // Small delay between jobs
    await new Promise(r => setTimeout(r, 3000));
  }

  console.log(`\n[batch] ===== SUMMARY =====`);
  console.log(`[batch] Total completed: ${completedJobs.length}/${JOBS.length}`);
  console.log(`[batch] Completed IDs: ${completedJobs.join(", ")}`);
}

main().catch(e => { console.error("[batch] Fatal:", e); process.exit(1); });
