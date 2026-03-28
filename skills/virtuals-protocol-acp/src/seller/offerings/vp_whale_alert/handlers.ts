import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";

const WORKSPACE = "/docker/openclaw-taan/data/.openclaw/workspace";
const PYTHON = `${WORKSPACE}/neo-env/bin/python`;

function runPython(script: string): string {
  try {
    const result = execSync(
      `cd ${WORKSPACE} && ${PYTHON} -c "${script.replace(/"/g, '\\"')}"`,
      { timeout: 60000, encoding: "utf-8" }
    );
    return result.trim();
  } catch (e: any) {
    return `ERROR: ${e.message?.slice(0, 200)}`;
  }
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const symbol = request?.symbol || "VIRTUAL";
  const includeDexPools = request?.include_dex_pools !== false;

  const script = `
import sys; sys.path.insert(0, '.')
import json
from datetime import datetime, timezone

report = {'symbol': '${symbol}', 'type': 'whale_alert', 'timestamp': datetime.now(timezone.utc).isoformat()}

# 1. Whale activity from Base chain
try:
    from tools.whale_monitor import fetch_whale_events
    whale = fetch_whale_events('${symbol}')
    report['whale_activity'] = {
        'whale_count': whale.get('whale_count', 0),
        'whale_volume_usd': whale.get('whale_volume_usd', 0),
        'signal': whale.get('signal', 'NEUTRAL'),
        'scanned_blocks': whale.get('scanned_blocks', 0),
        'large_txs': whale.get('large_txs', [])[:10]
    }
except Exception as e:
    report['whale_activity'] = {'error': str(e)}

# 2. DEX pool data (optional)
if ${includeDexPools ? "True" : "False"}:
    try:
        from tools.vp_onchain_data import fetch_dex_data
        dex = fetch_dex_data('${symbol}')
        pools = dex.get('pools', [])
        report['dex_pools'] = {
            'pool_count': len(pools),
            'price_usd': dex.get('price_usd', 0),
            'total_liquidity_usd': sum(p.get('liquidity_usd', 0) for p in pools),
            'volume_24h_usd': sum(p.get('volume_24h', 0) for p in pools),
            'top_pools': [{
                'dex': p.get('dex', ''),
                'pair': p.get('pair', ''),
                'liquidity_usd': p.get('liquidity_usd', 0),
                'volume_24h': p.get('volume_24h', 0),
                'price': p.get('price', 0)
            } for p in pools[:5]]
        }
    except Exception as e:
        report['dex_pools'] = {'error': str(e)}

# 3. Current price for context
try:
    from tools.market_data import MarketData
    md = MarketData()
    price = md.get_price('${symbol}')
    report['current_price'] = price
except Exception as e:
    report['current_price'] = {'error': str(e)}

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Whale alert scan failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  const symbol = request?.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL or AIXBT" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.symbol || "VIRTUAL";
  return `VP Whale Alert for ${symbol} — On-chain whale monitoring + DEX liquidity`;
}
