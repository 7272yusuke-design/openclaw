import { getClient } from "../src/lib/api/client";

async function main() {
  const { agentApi } = await getClient();
  
  // Full agent data
  const a: any = await agentApi.getById("019d7b3f-c2d8-7a52-839c-9629f4abb5dc");
  console.log("=== getById full keys ===");
  console.log("Top-level keys:", Object.keys(a).join(", "));
  console.log("\n=== Non-trivial top-level fields ===");
  for (const k of Object.keys(a)) {
    if (["offerings", "resources", "chains", "walletProviders", "description", "imageUrl"].includes(k)) continue;
    console.log(`  ${k}:`, JSON.stringify(a[k]));
  }
  
  // Browse (search) result — different fields
  const br = await agentApi.browse("NeoAutonomous");
  const found: any = br.data.find((x: any) => x.walletAddress?.toLowerCase() === "0x840cff9032a4ce29845e05aed510f0ca4ea16cab");
  if (found) {
    console.log("\n=== browse result keys ===");
    console.log("Top-level keys:", Object.keys(found).join(", "));
    console.log("\n=== browse Non-trivial fields ===");
    for (const k of Object.keys(found)) {
      if (["offerings", "resources", "chains", "description", "imageUrl"].includes(k)) continue;
      console.log(`  ${k}:`, JSON.stringify(found[k]));
    }
  } else {
    console.log("\n=== NeoAutonomous NOT FOUND in browse ===");
  }
}
main().catch(e => { console.error(e); process.exit(1); });
