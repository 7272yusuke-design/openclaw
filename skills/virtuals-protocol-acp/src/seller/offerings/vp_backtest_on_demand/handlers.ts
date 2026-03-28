import type { ExecuteJobResult, ValidationResult } from "../../runtime/offeringTypes.js";
import { execSync } from "child_process";

const WORKSPACE = "/docker/openclaw-taan/data/.openclaw/workspace";
const PYTHON = `${WORKSPACE}/neo-env/bin/python`;

function runPython(script: string): string {
  try {
    const result = execSync(
      `cd ${WORKSPACE} && ${PYTHON} -c "${script.replace(/"/g, '\\"')}"`,
      { timeout: 180000, encoding: "utf-8" }
    );
    return result.trim();
  } catch (e: any) {
    return `ERROR: ${e.message?.slice(0, 500)}`;
  }
}

export async function executeJob(request: any): Promise<ExecuteJobResult> {
  const symbol = request?.symbol || "VIRTUAL";
  const days = request?.timeframe_days || 30;

  const script = `
import sys; sys.path.insert(0, '.')
import json
from datetime import datetime, timezone
from tools.market_data import MarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest

sym = '${symbol}'
days = ${days}
report = {
    'symbol': sym,
    'type': 'backtest_on_demand',
    'timeframe_days': days,
    'timestamp': datetime.now(timezone.utc).isoformat()
}

# Fetch real OHLCV data
try:
    df = MarketData.fetch_ohlcv_custom(sym, days=days)
    df = FeatureBuilder.build_from_memory(df)
    report['data_points'] = len(df)
    report['data_range'] = f'{df.index[0]} to {df.index[-1]}' if hasattr(df.index[0], 'isoformat') else f'{len(df)} candles'
except Exception as e:
    report['error'] = f'Data fetch failed: {str(e)}'
    print(json.dumps(report))
    sys.exit(0)

# Run all 9 strategies
try:
    bt = CoreBacktest.run_all_strategies(df, symbol=sym, use_optuna=False)
    strategies = {}
    for name, r in bt['all_results'].items():
        strategies[name] = {
            'sharpe_raw': round(r.get('sharpe_raw', 0), 3),
            'sharpe_adj': round(r.get('sharpe', 0), 3),
            'win_rate': round(r.get('win_rate', 0), 1),
            'trades': r.get('trades', 0),
            'total_return': round(r.get('total_return', 0), 3),
            'max_drawdown': round(r.get('max_drawdown', 0), 3)
        }

    # Rank by sharpe_raw
    ranked = sorted(strategies.items(), key=lambda x: x[1]['sharpe_raw'], reverse=True)
    for i, (name, _) in enumerate(ranked):
        strategies[name]['rank'] = i + 1

    best = bt['best']
    positive = sum(1 for v in strategies.values() if v['sharpe_adj'] > 0)

    report['strategies'] = strategies
    report['best_strategy'] = {
        'name': best.get('strategy', 'N/A'),
        'sharpe_raw': round(best.get('sharpe_raw', 0), 3),
        'win_rate': round(best.get('win_rate', 0), 1),
        'trades': best.get('trades', 0)
    }
    report['summary'] = {
        'total_strategies': len(strategies),
        'positive_sharpe': positive,
        'negative_sharpe': len(strategies) - positive
    }

except Exception as e:
    report['error'] = f'Backtest failed: {str(e)}'

# Neo credentials
try:
    from tools.paper_wallet import PaperWallet
    pw = PaperWallet()
    hist = pw.state.get('history', [])
    buy_q = {}
    wins = 0; losses = 0
    for h in hist:
        s = h.get('symbol', '')
        if h['action'] == 'BUY':
            buy_q.setdefault(s, []).append(float(h['price']))
        elif h['action'] == 'SELL' and buy_q.get(s):
            bp = buy_q[s].pop(0)
            if float(h['price']) > bp: wins += 1
            else: losses += 1
    total_closed = wins + losses
    report['evaluator_credentials'] = {
        'neo_win_rate': round((wins/total_closed*100), 1) if total_closed else 0,
        'neo_closed_trades': total_closed,
        'methodology': '9-strategy parallel backtest (incl. gplearn), 4h OHLCV real data from GeckoTerminal'
    }
except:
    pass

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Backtest failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  const symbol = request?.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL or AIXBT" };
  }
  const days = request?.timeframe_days;
  if (days && ![30, 60, 90, 166].includes(days)) {
    return { valid: false, reason: "timeframe_days must be 30, 60, 90, or 166" };
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.symbol || "VIRTUAL";
  const days = request?.timeframe_days || 30;
  return `VP 9-Strategy Backtest for ${symbol} (${days}d) — powered by Neo`;
}
