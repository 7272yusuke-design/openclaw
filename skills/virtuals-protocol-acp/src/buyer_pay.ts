import { webcrypto } from "node:crypto";
if (typeof globalThis.crypto === "undefined") {
  (globalThis as any).crypto = webcrypto;
}
import AcpClientDefault, { AcpContractClientV2 } from "@virtuals-protocol/acp-node";
const AcpClient = (AcpClientDefault as any).default || AcpClientDefault;
import dotenv from "dotenv";
dotenv.config({ path: "/docker/openclaw-taan/data/.openclaw/workspace/.env" });

const jobId = parseInt(process.argv[2] || "0", 10);
if (!jobId) { console.error("Usage: buyer_pay.ts <jobId>"); process.exit(1); }

async function main() {
  // Use buyer's wallet - neo-test-buyer
  // We need buyer's private key... but we don't have it for OpenClaw buyer
  // Instead, use seller's SDK to check job status
  const contractClient = await AcpContractClientV2.build(
    process.env.WHITELISTED_WALLET_PRIVATE_KEY! as `0x${string}`,
    parseInt(process.env.SESSION_ENTITY_KEY_ID!, 10),
    process.env.NATIVE_AGENT_WALLET_ADDRESS! as `0x${string}`
  );
  const acpClient = new AcpClient({ acpContractClient: contractClient });
  const job = await acpClient.getJobById(jobId);
  if (!job) { console.error("Job not found"); process.exit(1); }
  console.log(`Job ${job.id}: phase=${job.phase}, memos=${job.memos.length}`);
  for (const m of job.memos) {
    console.log(`  Memo ${m.id}: nextPhase=${m.nextPhase} status=${m.status}`);
  }
}
main().catch(e => { console.error(e); process.exit(1); });
