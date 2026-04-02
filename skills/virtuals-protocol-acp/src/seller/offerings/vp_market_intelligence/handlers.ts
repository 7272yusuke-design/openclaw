import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";

const WORKSPACE = "/docker/openclaw-taan/data/.openclaw/workspace";
const PYTHON = `${WORKSPACE}/neo-env/bin/python`;

function runPython(script: string, timeoutMs: number = 180000): string {
  try {
    const result = execSync(
      `cd ${WORKSPACE} && ${PYTHON} -c "${script.replace(/"/g, '\\"')}"`,
      { timeout: timeoutMs, encoding: "utf-8" }
    );
    return result.trim();
  } catch (e: any) {
    return `ERROR: ${e.message?.slice(0, 500)}`;
  }
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const symbol = request?.symbol || "VIRTUAL";
  const mode = request?.mode || "quick";

  if (mode === "full") {
    // Full mode: TrinityCouncil with analysis_only=True
    const script = `
import sys, json; sys.path.insert(0, '.')
from datetime import datetime, timezone
report = {'symbol': '${symbol}', 'mode': 'full', 'timestamp': datetime.now(timezone.utc).isoformat()}
try:
    from agents.trinity_council import TrinityCouncil
    tc = TrinityCouncil()
    result = tc.run(sentiment_score=0.5, context='ACP Market Intelligence request', target_symbol='${symbol}', analysis_only=True)
    report['verdict'] = result.get('verdict', 'WAIT')
    report['confidence'] = result.get('confidence', 0)
    report['key_factor'] = result.get('key_factor', '')
    report['price'] = result.get('price', 0)
    report['scoring_breakdown'] = result.get('scoring_breakdown', {})
    report['bull_case'] = result.get('bull_case', 'N/A')
    report['bear_case'] = result.get('bear_case', 'N/A')
    report['neo_synthesis'] = result.get('neo_synthesis', 'N/A')
    report['sentiment_detail'] = result.get('sentiment_detail', {})
    report['backtest_summary'] = result.get('backtest_summary', {})
    report['exit_profile'] = result.get('exit_profile', {})
    report['best_strategy'] = result.get('best_strategy', 'N/A')
except Exception as e:
    report['error'] = str(e)[:300]
    report['verdict'] = 'ERROR'
# Neo track record
try:
    from tools.paper_wallet import PaperWallet
    pw = PaperWallet()
    hist = pw.state.get('history', [])
    buy_q = {}; wins = 0; losses = 0
    for h in hist:
        s = h.get('symbol', '')
        if h['action'] == 'BUY': buy_q.setdefault(s, []).append(float(h['price']))
        elif h['action'] == 'SELL' and buy_q.get(s):
            if float(h['price']) > buy_q[s].pop(0): wins += 1
            else: losses += 1
    total = wins + losses
    report['neo_track_record'] = {'win_rate': round(wins/total*100, 1) if total else 0, 'closed_trades': total, 'total_trades': len(hist)}
except: pass
print(json.dumps(report))
`;
    const output = runPython(script, 240000);
    try {
      return { deliverable: JSON.stringify(JSON.parse(output)) };
    } catch {
      return { deliverable: JSON.stringify({ error: "Full analysis failed", raw: output.slice(0, 500) }) };
    }

  } else {
    // Quick mode: technicals + sentiment + backtest, no Council
    const script = `
import sys, json; sys.path.insert(0, '.')
from datetime import datetime, timezone
report = {'symbol': '${symbol}', 'mode': 'quick', 'timestamp': datetime.now(timezone.utc).isoformat()}
# Technicals
try:
    from tools.market_data import MarketData
    from feature_engineering.build_features import FeatureBuilder
    df = MarketData.fetch_ohlcv_custom('${symbol}', days=30)
    df = FeatureBuilder.build_from_memory(df)
    last = df.iloc[-1]
    report['price'] = round(float(last['close']), 6)
    report['technicals'] = {
        'rsi_14': round(float(last.get('rsi_14', 0)), 1),
        'ma20': round(float(last.get('ma20', 0)), 6),
        'ma50': round(float(last.get('ma50', 0)), 6),
    }
    report['data_points'] = len(df)
except Exception as e:
    report['technicals_error'] = str(e)[:200]
# Backtest
try:
    from research.backtests.run_backtest import CoreBacktest
    bt = CoreBacktest.run_all_strategies(df, symbol='${symbol}', use_optuna=False)
    best = bt['best']
    positive = sum(1 for v in bt['all_results'].values() if v.get('sharpe', 0) > 0)
    report['backtest'] = {
        'best_strategy': best.get('strategy', 'N/A'),
        'best_sharpe': round(best.get('sharpe_raw', 0), 3),
        'best_win_rate': round(best.get('win_rate', 0), 1),
        'positive_strategies': f'{positive}/{len(bt["all_results"])}',
    }
    # Derive signal from backtest + technicals
    _rsi = report.get('technicals', {}).get('rsi_14', 50)
    _sharpe = best.get('sharpe_raw', 0)
    if _sharpe > 0.5 and _rsi < 35:
        report['signal'] = 'BUY'
    elif _sharpe < -0.5 or _rsi > 70:
        report['signal'] = 'SELL'
    else:
        report['signal'] = 'WAIT'
except Exception as e:
    report['backtest_error'] = str(e)[:200]
    report['signal'] = 'WAIT'
# Sentiment
try:
    from tools.crypto_news import CryptoNews
    from tools.finbert_sentiment import get_finbert_score
    headlines = CryptoNews.fetch_all()
    all_titles = [h for h in headlines if h.strip()][:30]
    fb = get_finbert_score(all_titles)
    report['sentiment'] = {
        'finbert_score': round(fb.get('score', 0), 3),
        'finbert_label': fb.get('label', 'neutral'),
        'articles': fb.get('count', 0),
    }
except Exception as e:
    report['sentiment_error'] = str(e)[:200]
# Fear & Greed
try:
    import urllib.request
    resp = urllib.request.urlopen('https://api.alternative.me/fng/?limit=1', timeout=10)
    fg = json.loads(resp.read())
    report['fear_greed'] = {'value': int(fg['data'][0]['value']), 'label': fg['data'][0]['value_classification']}
except: pass
# Exit profile for best strategy
try:
    from core.config import EXIT_PROFILES, STRATEGY_TO_EXIT_PROFILE, EXIT_PROFILE_DEFAULT
    _best_name = report.get('backtest', {}).get('best_strategy', 'none')
    _cat = STRATEGY_TO_EXIT_PROFILE.get(_best_name, EXIT_PROFILE_DEFAULT)
    _ep = EXIT_PROFILES.get(_cat, {})
    report['exit_profile'] = {'category': _cat, 'sl_pct': _ep.get('sl_pct', 5.0), 'trailing_start': _ep.get('trailing_start', 5.0), 'hard_tp_pct': _ep.get('hard_tp_pct', 14.0)}
except: pass
# Neo track record
try:
    from tools.paper_wallet import PaperWallet
    pw = PaperWallet()
    hist = pw.state.get('history', [])
    buy_q = {}; wins = 0; losses = 0
    for h in hist:
        s = h.get('symbol', '')
        if h['action'] == 'BUY': buy_q.setdefault(s, []).append(float(h['price']))
        elif h['action'] == 'SELL' and buy_q.get(s):
            if float(h['price']) > buy_q[s].pop(0): wins += 1
            else: losses += 1
    total = wins + losses
    report['neo_track_record'] = {'win_rate': round(wins/total*100, 1) if total else 0, 'closed_trades': total}
except: pass
print(json.dumps(report))
`;
    const output = runPython(script, 120000);
    try {
      return { deliverable: JSON.stringify(JSON.parse(output)) };
    } catch {
      return { deliverable: JSON.stringify({ error: "Quick analysis failed", raw: output.slice(0, 500) }) };
    }
  }
}

export function validateRequirements(request: any): ValidationResult {
  const symbol = request?.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT", "BTC", "ETH"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL, AIXBT, BTC, or ETH" };
  }
  const mode = request?.mode;
  if (mode && !["quick", "full"].includes(mode)) {
    return { valid: false, reason: "mode must be quick or full" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.symbol || "VIRTUAL";
  const mode = request?.mode || "quick";
  return `Neo Market Intelligence (${mode}) for ${symbol} — TrinityCouncil powered`;
}
