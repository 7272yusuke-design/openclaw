import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";

const WORKSPACE = "/docker/openclaw-taan/data/.openclaw/workspace";
const PYTHON = `${WORKSPACE}/neo-env/bin/python`;

function runPython(script: string): string {
  try {
    const result = execSync(
      `cd ${WORKSPACE} && ${PYTHON} -c "${script.replace(/"/g, '\\"')}"`,
      { timeout: 120000, encoding: "utf-8" }
    );
    return result.trim();
  } catch (e: any) {
    return `ERROR: ${e.message?.slice(0, 200)}`;
  }
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  const depth = request?.requirements?.depth || "summary";

  // Generate report via Neo's existing modules
  const script = `
import sys; sys.path.insert(0, '.')
import json
from tools.market_data import MarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest
from tools.paper_wallet import PaperWallet

sym = '${symbol}'
report = {'symbol': sym, 'depth': '${depth}'}

# Price + technicals
try:
    df = MarketData.fetch_ohlcv_custom(sym, days=30)
    df = FeatureBuilder.build_from_memory(df)
    last = df.iloc[-1]
    report['price'] = round(float(last['close']), 6)
    report['rsi_14'] = round(float(last.get('rsi_14', 0)), 1)
    report['ma20'] = round(float(last.get('ma20', 0)), 6)
    report['ma50'] = round(float(last.get('ma50', 0)), 6)
    report['data_points'] = len(df)
except Exception as e:
    report['technicals_error'] = str(e)

# Backtest
try:
    bt = CoreBacktest.run_all_strategies(df, symbol=sym, use_optuna=False)
    best = bt['best']
    report['best_strategy'] = best.get('strategy', 'N/A')
    report['best_sharpe'] = best.get('sharpe_raw', 0)
    report['best_win_rate'] = best.get('win_rate', 0)
    report['best_trades'] = best.get('trades', 0)
    positive = sum(1 for v in bt['all_results'].values() if v.get('sharpe', 0) > 0)
    report['positive_strategies'] = f'{positive}/8'
except Exception as e:
    report['backtest_error'] = str(e)

# Sentiment
try:
    from agents.sentiment_agent import SentimentAgent
    sa = SentimentAgent()
    sent = sa.analyze()
    report['sentiment_score'] = round(sent.get('composite_score', 0), 3)
    report['fear_greed'] = sent.get('fear_greed_value', 'N/A')
    report['btc_trend'] = sent.get('btc_trend', 'N/A')
except Exception as e:
    report['sentiment_error'] = str(e)

# Performance
try:
    pw = PaperWallet()
    hist = pw.state.get('history', [])
    sells = [h for h in hist if h.get('action') == 'SELL']
    wins = sum(1 for h in sells if h.get('pnl_pct', 0) > 0)
    wr = (wins / len(sells) * 100) if sells else 0
    report['neo_trades'] = len(hist)
    report['neo_win_rate'] = round(wr, 1)
except Exception as e:
    report['performance_error'] = str(e)

# Full depth: add all strategy results
if '${depth}' == 'full':
    try:
        report['all_strategies'] = {
            name: {'sharpe': r.get('sharpe_raw', 0), 'trades': r.get('trades', 0), 'win_rate': r.get('win_rate', 0)}
            for name, r in bt['all_results'].items()
        }
    except: pass

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Report generation failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  const symbol = request?.requirements?.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL or AIXBT" };
  }
  const depth = request?.requirements?.depth;
  if (depth && !["summary", "full"].includes(depth)) {
    return { valid: false, reason: "depth must be summary or full" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  return `VP Market Analysis Report for ${symbol} — powered by TrinityCouncil`;
}
