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
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  const includeHeadlines = request?.requirements?.include_headlines || false;

  const script = `
import sys; sys.path.insert(0, '.')
import json
from datetime import datetime, timezone

report = {'symbol': '${symbol}', 'type': 'sentiment_scan', 'timestamp': datetime.now(timezone.utc).isoformat()}

# 1. FinBERT sentiment from RSS news
try:
    from tools.crypto_news import CryptoNews
    headlines = CryptoNews.fetch_all()
    # Filter VP-relevant headlines
    vp_keywords = ['virtual', 'virtuals', 'aixbt', 'vp ', 'agent', 'acp']
    sym_lower = '${symbol}'.lower()
    vp_headlines = [h for h in headlines if any(k in h.lower() for k in vp_keywords + [sym_lower])]
    all_titles = [h for h in headlines if h.strip()]

    from tools.finbert_sentiment import get_finbert_score
    # Overall market sentiment
    market_sent = get_finbert_score(all_titles[:30])
    report['market_sentiment'] = {
        'score': market_sent['score'],
        'label': market_sent['label'],
        'positive_ratio': market_sent['positive_ratio'],
        'negative_ratio': market_sent['negative_ratio'],
        'neutral_ratio': market_sent['neutral_ratio'],
        'articles_analyzed': market_sent['count']
    }
    # VP-specific sentiment
    if vp_headlines:
        vp_sent = get_finbert_score(vp_headlines[:15])
        report['vp_sentiment'] = {
            'score': vp_sent['score'],
            'label': vp_sent['label'],
            'articles_found': vp_sent['count']
        }
    else:
        report['vp_sentiment'] = {'score': 0.0, 'label': 'no_data', 'articles_found': 0}

    if ${includeHeadlines ? "True" : "False"}:
        report['top_headlines'] = all_titles[:10]
        if vp_headlines:
            report['vp_headlines'] = vp_headlines[:5]
except Exception as e:
    report['finbert_error'] = str(e)

# 2. Fear & Greed Index
try:
    import urllib.request
    resp = urllib.request.urlopen('https://api.alternative.me/fng/?limit=1', timeout=10)
    fg_data = json.loads(resp.read())
    report['fear_greed'] = {
        'value': int(fg_data['data'][0]['value']),
        'classification': fg_data['data'][0]['value_classification']
    }
except Exception as e:
    report['fear_greed'] = {'error': str(e)}

# 3. BTC 3-tier trend
try:
    from tools.market_data import MarketData
    btc = MarketData.fetch_btc_trend()
    report['btc_trend'] = {
        'price_usd': btc.get('price', 0),
        'change_24h': btc.get('change_24h', 0),
        'change_30d': btc.get('change_30d', 0),
        'change_180d': btc.get('change_180d', 0),
        'trend': btc.get('trend', 'unknown')
    }
except Exception as e:
    report['btc_trend'] = {'error': str(e)}

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Sentiment scan failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  const symbol = request?.requirements?.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL or AIXBT" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  return `VP Sentiment Scan for ${symbol} — FinBERT + Fear&Greed + BTC trend`;
}
