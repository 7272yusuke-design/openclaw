import { getClient } from "../src/lib/api/client";

async function main() {
  const { agentApi } = await getClient();
  const a: any = await agentApi.getById("019d7b3f-c2d8-7a52-839c-9629f4abb5dc");
  for (const o of (a.offerings || [])) {
    if (o.name === "offering_audit" || o.name === "vp_sentiment_scan") {
      console.log(`=== ${o.name} ($${o.priceValue}) ===`);
      console.log("description:", o.description?.substring(0, 200));
      console.log("requirements:", JSON.stringify(o.requirements, null, 2));
      console.log("");
    }
  }
}
main().catch(e => { console.error(e); process.exit(1); });
