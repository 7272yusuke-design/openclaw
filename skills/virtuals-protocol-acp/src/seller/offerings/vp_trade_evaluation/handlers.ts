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
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  const evalType = request?.requirements?.evaluation_type || "strategy_audit";
  const trades = JSON.stringify(request?.requirements?.trades || []);
  const claimedMetrics = JSON.stringify(request?.requirements?.claimed_metrics || {});
  const strategyParams = JSON.stringify(request?.requirements?.strategy_params || {});

  const script = `
import sys; sys.path.insert(0, '.')
import json, math
from datetime import datetime, timezone
from tools.market_data import MarketData
from feature_engineering.build_features import FeatureBuilder
from research.backtests.run_backtest import CoreBacktest

sym = '${symbol}'
eval_type = '${evalType}'
trades_raw = json.loads('${trades.replace(/'/g, "\\'")}')
claimed = json.loads('${claimedMetrics.replace(/'/g, "\\'")}')
strat_params = json.loads('${strategyParams.replace(/'/g, "\\'")}')

report = {
    'evaluator': 'Neo TrinityCouncil',
    'symbol': sym,
    'evaluation_type': eval_type,
    'timestamp': datetime.now(timezone.utc).isoformat(),
    'verdict': 'PENDING',
    'scores': {},
    'details': {},
    'recommendations': []
}

# Load real market data
try:
    df = MarketData.fetch_ohlcv_custom(sym, days=30)
    df = FeatureBuilder.build_from_memory(df)
    report['data_points'] = len(df)
    report['data_range'] = f"{df.index[0]} to {df.index[-1]}" if hasattr(df.index[0], 'isoformat') else f"{len(df)} candles"
except Exception as e:
    report['error'] = f'Market data fetch failed: {str(e)}'
    report['verdict'] = 'ERROR'
    print(json.dumps(report))
    sys.exit(0)

if eval_type == 'strategy_audit':
    # Run all 9 strategies + compare
    try:
        bt = CoreBacktest.run_all_strategies(df, symbol=sym, use_optuna=False)
        all_results = {}
        for name, r in bt['all_results'].items():
            all_results[name] = {
                'sharpe': round(r.get('sharpe_raw', 0), 3),
                'win_rate': round(r.get('win_rate', 0), 1),
                'trades': r.get('trades', 0),
                'total_return': round(r.get('total_return', 0), 3)
            }
        best = bt['best']
        report['details']['all_strategies'] = all_results
        report['details']['best_strategy'] = best.get('strategy', 'N/A')
        report['details']['best_sharpe'] = round(best.get('sharpe_raw', 0), 3)
        positive = sum(1 for v in bt['all_results'].values() if v.get('sharpe', 0) > 0)
        report['scores']['strategy_diversity'] = f'{positive}/{len(bt["all_results"])} positive Sharpe'

        # If client provided strategy params, evaluate specifically
        if strat_params.get('name'):
            sname = strat_params['name']
            if sname in all_results:
                client_strat = all_results[sname]
                report['scores']['client_strategy_sharpe'] = client_strat['sharpe']
                report['scores']['client_strategy_win_rate'] = client_strat['win_rate']
                report['scores']['client_strategy_rank'] = sorted(
                    all_results.keys(),
                    key=lambda k: all_results[k]['sharpe'], reverse=True
                ).index(sname) + 1
                if client_strat['sharpe'] <= 0:
                    report['recommendations'].append(f'Strategy {sname} has negative Sharpe. Consider switching to {best.get("strategy")}.')
            else:
                report['details']['client_strategy_note'] = f'Strategy {sname} not in standard set. Run custom backtest for full evaluation.'

        report['verdict'] = 'PASS' if best.get('sharpe_raw', 0) > 0 else 'CAUTION'
    except Exception as e:
        report['error'] = f'Backtest failed: {str(e)}'
        report['verdict'] = 'ERROR'

elif eval_type == 'trade_history_verify':
    # Verify claimed trades against real price data
    try:
        closes = df['close'].tolist()
        price_min = min(closes)
        price_max = max(closes)

        verified_trades = []
        total_pnl = 0
        wins = 0
        losses = 0
        buy_stack = []

        for t in trades_raw:
            action = t.get('action', '').upper()
            price = float(t.get('price', 0))
            amount = float(t.get('amount_usd', 0))

            # Check price plausibility
            plausible = price_min * 0.8 <= price <= price_max * 1.2
            vt = {'action': action, 'price': price, 'amount_usd': amount, 'price_plausible': plausible}

            if action == 'BUY':
                buy_stack.append({'price': price, 'amount': amount})
            elif action == 'SELL' and buy_stack:
                buy = buy_stack.pop(0)
                pnl_pct = ((price - buy['price']) / buy['price']) * 100
                vt['matched_buy_price'] = buy['price']
                vt['pnl_pct'] = round(pnl_pct, 2)
                total_pnl += pnl_pct
                if pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1

            verified_trades.append(vt)

        total_closed = wins + losses
        verified_wr = round((wins / total_closed * 100), 1) if total_closed > 0 else 0

        report['details']['verified_trades'] = len(verified_trades)
        report['details']['closed_pairs'] = total_closed
        report['details']['open_positions'] = len(buy_stack)
        report['scores']['verified_win_rate'] = verified_wr
        report['scores']['verified_total_pnl'] = round(total_pnl, 2)
        report['scores']['implausible_prices'] = sum(1 for vt in verified_trades if not vt.get('price_plausible', True))

        # Compare with claimed metrics
        if claimed.get('win_rate') is not None:
            diff = abs(claimed['win_rate'] - verified_wr)
            report['scores']['win_rate_discrepancy'] = round(diff, 1)
            if diff > 10:
                report['recommendations'].append(f'Claimed win rate {claimed["win_rate"]}% differs from verified {verified_wr}% by {diff:.1f}pp. Investigate methodology.')

        if claimed.get('total_return') is not None:
            report['scores']['claimed_total_return'] = claimed['total_return']

        # Verdict
        if report['scores'].get('implausible_prices', 0) > len(verified_trades) * 0.2:
            report['verdict'] = 'FAIL'
            report['recommendations'].append('Over 20% of trade prices are outside plausible range. Data integrity concern.')
        elif total_closed < 5:
            report['verdict'] = 'INSUFFICIENT_DATA'
            report['recommendations'].append('Fewer than 5 closed trades. Insufficient for reliable evaluation.')
        elif verified_wr >= 50 and total_pnl > 0:
            report['verdict'] = 'PASS'
        else:
            report['verdict'] = 'CAUTION'
            report['recommendations'].append('Win rate or total PnL below threshold. Review risk management.')

    except Exception as e:
        report['error'] = f'Verification failed: {str(e)}'
        report['verdict'] = 'ERROR'

elif eval_type == 'signal_quality':
    # Evaluate buy/sell signals against what actually happened
    try:
        closes = df['close'].tolist()
        rsi_vals = df['rsi_14'].tolist() if 'rsi_14' in df.columns else []
        last_price = closes[-1] if closes else 0

        correct_signals = 0
        total_signals = 0

        for t in trades_raw:
            action = t.get('action', '').upper()
            price = float(t.get('price', 0))

            if action == 'BUY':
                # Was buying at this price a good idea? Check if price went up after
                if last_price > price * 1.01:
                    correct_signals += 1
                total_signals += 1
            elif action == 'SELL':
                # Was selling correct? Check if price went down after
                if last_price < price * 0.99:
                    correct_signals += 1
                total_signals += 1

        signal_accuracy = round((correct_signals / total_signals * 100), 1) if total_signals > 0 else 0

        report['scores']['signal_accuracy'] = signal_accuracy
        report['scores']['total_signals_evaluated'] = total_signals
        report['scores']['correct_signals'] = correct_signals

        # Compare with Neo's own signals
        try:
            bt = CoreBacktest.run_all_strategies(df, symbol=sym, use_optuna=False)
            best = bt['best']
            report['details']['neo_best_strategy'] = best.get('strategy', 'N/A')
            report['details']['neo_best_sharpe'] = round(best.get('sharpe_raw', 0), 3)
            report['details']['neo_best_win_rate'] = round(best.get('win_rate', 0), 1)
        except:
            pass

        if total_signals < 3:
            report['verdict'] = 'INSUFFICIENT_DATA'
            report['recommendations'].append('Submit at least 3 signals for meaningful evaluation.')
        elif signal_accuracy >= 60:
            report['verdict'] = 'PASS'
        elif signal_accuracy >= 40:
            report['verdict'] = 'CAUTION'
            report['recommendations'].append('Signal accuracy below 60%. Consider refining entry/exit criteria.')
        else:
            report['verdict'] = 'FAIL'
            report['recommendations'].append('Signal accuracy below 40%. Strategy may be counterproductive.')

    except Exception as e:
        report['error'] = f'Signal evaluation failed: {str(e)}'
        report['verdict'] = 'ERROR'

# Add Neo credibility stamp
from tools.paper_wallet import PaperWallet
try:
    pw = PaperWallet()
    hist = pw.state.get('history', [])
    # FIFO matching for accurate win rate
    buy_q = {}
    wins = 0
    losses = 0
    for h in hist:
        s = h.get('symbol', '')
        if h.get('action') == 'BUY':
            buy_q.setdefault(s, []).append(float(h.get('price', 0)))
        elif h.get('action') == 'SELL' and buy_q.get(s):
            buy_price = buy_q[s].pop(0)
            sell_price = float(h.get('price', 0))
            if sell_price > buy_price:
                wins += 1
            else:
                losses += 1
    total_closed = wins + losses
    neo_wr = round((wins / total_closed * 100), 1) if total_closed > 0 else 0
    report['evaluator_credentials'] = {
        'neo_total_trades': len(hist),
        'neo_closed_trades': total_closed,
        'neo_win_rate': neo_wr,
        'methodology': '9-strategy parallel backtest (incl. gplearn), FIFO P&L matching, 4h OHLCV real data from GeckoTerminal'
    }
except:
    report['evaluator_credentials'] = {'note': 'Credentials unavailable'}

if not report.get('recommendations'):
    report['recommendations'].append('No issues detected.')

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Evaluation failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  const reqs = request?.requirements;
  if (!reqs) {
    return { valid: false, reason: "Missing requirements" };
  }

  const symbol = reqs.symbol;
  if (!symbol || !["VIRTUAL", "AIXBT"].includes(symbol)) {
    return { valid: false, reason: "symbol must be VIRTUAL or AIXBT" };
  }

  const evalType = reqs.evaluation_type;
  if (!evalType || !["strategy_audit", "trade_history_verify", "signal_quality"].includes(evalType)) {
    return { valid: false, reason: "evaluation_type must be strategy_audit, trade_history_verify, or signal_quality" };
  }

  // trade_history_verify and signal_quality require trades array
  if ((evalType === "trade_history_verify" || evalType === "signal_quality") && (!reqs.trades || !Array.isArray(reqs.trades) || reqs.trades.length === 0)) {
    return { valid: false, reason: `${evalType} requires a non-empty trades array` };
  }

  return { valid: true };
}

export function requestPayment(request: any): string {
  const symbol = request?.requirements?.symbol || "VIRTUAL";
  const evalType = request?.requirements?.evaluation_type || "evaluation";
  return `Neo Trade Evaluation: ${evalType} for ${symbol}`;
}
