import { getClient } from "../src/lib/api/client";

async function main() {
  const { agentApi } = await getClient();
  const a: any = await agentApi.getById("019d7b3f-c2d8-7a52-839c-9629f4abb5dc");
  console.log("=== NeoAutonomous offerings (price順) ===");
  const sorted = (a.offerings || []).slice().sort((x: any, y: any) =>
    parseFloat(String(x.priceValue)) - parseFloat(String(y.priceValue))
  );
  for (const o of sorted) {
    const price = String(o.priceValue).padStart(8);
    console.log(`  $${price} | type=${o.priceType} | hidden=${o.isHidden} | ${o.name}`);
  }
}
main().catch(e => { console.error(e); process.exit(1); });
