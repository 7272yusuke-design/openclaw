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
  const lookbackDays = Math.min(90, Math.max(7, request?.lookback_days || 30));
  const zEntry = request?.z_entry || 2.0;
  const zExit = request?.z_exit || 0.5;

  const script = `
import sys; sys.path.insert(0, '.')
import json
from datetime import datetime, timezone
from research.n1_pair_trade import calc_pair_signal

report = {'type': 'correlation_risk', 'pair': 'VIRTUAL/AIXBT', 'timestamp': datetime.now(timezone.utc).isoformat()}

try:
    sig = calc_pair_signal(lookback_days=${lookbackDays}, z_entry=${zEntry}, z_exit=${zExit})
    report['signal'] = sig.get('signal', 'ERROR')
    report['z_score'] = sig.get('z_score', 0)
    report['spread'] = sig.get('spread', 0)
    report['spread_mean'] = sig.get('spread_mean', 0)
    report['spread_std'] = sig.get('spread_std', 0)
    report['recent_corr'] = sig.get('recent_corr', 0)
    report['recommendation'] = sig.get('recommendation', '')
    report['prices'] = {'VIRTUAL': sig.get('v_price', 0), 'AIXBT': sig.get('a_price', 0)}

    # Risk level classification
    corr = sig.get('recent_corr', 0)
    z = abs(sig.get('z_score', 0))
    if corr < 0.3 or z > 3.0:
        report['risk_level'] = 'DANGER'
        report['risk_note'] = 'Correlation breakdown or extreme Z-score — avoid correlated positions'
    elif corr < 0.5 or z > 2.0:
        report['risk_level'] = 'WARNING'
        report['risk_note'] = 'Weakening correlation or elevated spread — reduce exposure'
    else:
        report['risk_level'] = 'SAFE'
        report['risk_note'] = 'Normal correlation regime — correlated positions acceptable'
except Exception as e:
    report['error'] = str(e)

print(json.dumps(report))
`;

  const output = runPython(script);

  let report: any;
  try {
    report = JSON.parse(output);
  } catch {
    return { deliverable: JSON.stringify({ error: "Correlation risk analysis failed", raw: output.slice(0, 500) }) };
  }

  return { deliverable: JSON.stringify(report) };
}

export function validateRequirements(request: any): ValidationResult {
  if (request?.lookback_days !== undefined) {
    const lb = Number(request.lookback_days);
    if (isNaN(lb) || lb < 7 || lb > 90) {
      return { valid: false, reason: "lookback_days must be between 7 and 90" };
    }
  }
  return { valid: true };
}

export function requestPayment(request: any): string {
  const days = request?.lookback_days || 30;
  return `VP Correlation Risk — VIRTUAL/AIXBT pair analysis (${days}d lookback)`;
}
