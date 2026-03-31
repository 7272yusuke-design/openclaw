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

async function main() {
  console.log("[buyer] Initializing Native Buyer...");
  const contractClient = await AcpContractClientV2.build(
    process.env.BUYER_WHITELISTED_WALLET_PRIVATE_KEY! as `0x${string}`,
    parseInt(process.env.BUYER_SESSION_ENTITY_KEY_ID!, 10),
    process.env.BUYER_AGENT_WALLET_ADDRESS! as `0x${string}`
  );

  const acpClient = new AcpClient({
    acpContractClient: contractClient,
    onNewTask: (job: any, memo: any) => {
      console.log(`[buyer] onNewTask: job ${job.id} phase=${AcpJobPhases[job.phase]}`);
      if (job.phase === AcpJobPhases.NEGOTIATION) {
        console.log(`[buyer] Auto-paying job ${job.id}...`);
        job.payAndAcceptRequirement("Payment confirmed").then(() => {
          console.log(`[buyer] Payment sent for job ${job.id} ✅`);
        }).catch((e: any) => console.error(`[buyer] Pay error:`, e));
      }
    },
  });

  const usdcFare = await Fare.fromContractAddress(USDC_BASE as `0x${string}`);
  const fareAmount = new FareAmount(0.3, usdcFare);

  console.log("[buyer] Creating job with NeoAutonomous seller...");
  const jobId = await acpClient.initiateJob(
    SELLER_WALLET as `0x${string}`,
    JSON.stringify({
      _offeringName: "offering_audit",
      target_wallet: SELLER_WALLET,
      offering_name: "profile_seo",
      offering_description: "Test offering for audit",
      offering_price: 0.3
    }),
    fareAmount,
    undefined,
    new Date(Date.now() + 30 * 60 * 1000),
    "offering_audit"
  );

  console.log(`[buyer] Job created: ${jobId}`);
  console.log("[buyer] Waiting for seller to process...");

  for (let i = 0; i < 12; i++) {
    await new Promise(r => setTimeout(r, 10000));
    try {
      const job = await acpClient.getJobById(jobId);
      if (job) {
        console.log(`[buyer] Poll: job ${job.id} phase=${AcpJobPhases[job.phase]}`);
        if (job.phase === AcpJobPhases.COMPLETED) {
          console.log("[buyer] Job COMPLETED ✅");
          process.exit(0);
        }
      }
    } catch (e) { /* ignore */ }
  }
  console.log("[buyer] Timeout — check logs");
}

main().catch(e => { console.error("[buyer] Fatal:", e); process.exit(1); });
