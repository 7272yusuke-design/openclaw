import { getClient } from "../src/lib/api/client";

async function main() {
  const { agentApi } = await getClient();

  console.log("=== getById: NeoAutonomous ===");
  const agent: any = await agentApi.getById("019d7b3f-c2d8-7a52-839c-9629f4abb5dc");
  console.log(JSON.stringify({
    name: agent.name,
    wallet: agent.walletAddress,
    isHidden: agent.isHidden,
    lastActiveAt: agent.lastActiveAt,
    chains: agent.chains,
    resources: agent.resources?.map((r: any) => ({ name: r.name, url: r.url })),
  }, null, 2));

  console.log("\n=== browse 'NeoAutonomous' ===");
  const browse = await agentApi.browse("NeoAutonomous");
  for (const a of browse.data) {
    console.log(JSON.stringify({
      name: a.name,
      wallet: a.walletAddress,
      lastActiveAt: a.lastActiveAt,
      acpV2AgentId: a.chains?.find((c: any) => c.chainId === 8453)?.acpV2AgentId,
    }));
  }
}

main().catch((e) => { console.error("ERROR:", e); process.exit(1); });
