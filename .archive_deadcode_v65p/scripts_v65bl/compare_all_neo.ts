import { getClient } from "../src/lib/api/client";

const NEO_IDS = [
  { name: "NeoAutonomous (主役・問題児)", id: "019d7b3f-c2d8-7a52-839c-9629f4abb5dc" },
  { name: "neo-test-buyer-v2 (正常稼働)", id: "019d76d4-4e69-76c4-99d7-b90c64988af3" },
  { name: "Neo (旧)",                    id: "019d7659-6dd1-7067-a5ff-d74f567a3961" },
  { name: "neo-test-buyer",              id: "019d7bb4-d669-7809-a171-e6996c632eea" },
];

async function main() {
  const { agentApi } = await getClient();
  for (const { name, id } of NEO_IDS) {
    try {
      const a: any = await agentApi.getById(id);
      const ch = a.chains?.[0] || {};
      console.log(JSON.stringify({
        name,
        wallet: a.walletAddress,
        lastActiveAt: a.lastActiveAt,
        isHidden: a.isHidden,
        acpV2AgentId: ch.acpV2AgentId,
        chainId: ch.chainId,
      }));
    } catch (e: any) {
      console.log(`${name}: ERROR ${e.message}`);
    }
  }
}
main().catch((e) => { console.error("ERR:", e); process.exit(1); });
