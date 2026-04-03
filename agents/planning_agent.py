"""
PlanningCrew — 戦略リスク評価エージェント (Phase 1e)

Neo内部データ（H.2統計、EvolveRルール、ChromaDB記憶、scoring_adjustments）と
マクロ資本フローデータ（F5: お盆フレームワーク）を統合し、
構造化されたリスク評価+資本フローフェーズ判定を出力する。

LLMは「分析官」であり「判断者」ではない。
数値判断（confidence等）はE3統計エンジンとPhase 4bルールに委ねる。

TrinityCouncilのPhase 1e（バックテスト前）で呼び出され、
Phase 3の三者協議とPhase 4bのスコアリングに注入される。
"""
import sys; sys.path.insert(0, '.')
import json
import os
from datetime import datetime, timezone
from core.model_factory import ModelFactory


def run_strategic_assessment(symbol: str, current_price: float,
                              sentiment_score: float, sentiment_label: str,
                              bt_confidence: str = "NONE",
                              formatted_precedents: str = "",
                              failure_summary: str = "",
                              btc_context: str = "") -> dict:
    """
    内部データに基づく戦略リスク評価を実行。
    
    Returns:
        dict with keys:
        - risk_level: "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
        - risk_factors: list of str (最大5つ)
        - opportunity_factors: list of str (最大3つ)
        - capital_flow_phase: "RISK_OFF_ACCUMULATE" / "RISK_ON_RIDE" / "RISK_ON_DISTRIBUTE" / "RISK_OFF_EXIT"
        - macro_summary: str (30字以内のマクロ環境要約)
        - worst_case: str (最悪シナリオ)
        - mitigation: str (対策)
        - reasoning: str (50字以内の根拠)
    """
    # --- 内部データ収集 ---
    # 1. H.2統計
    h2_summary = ""
    try:
        from research.h2_trade_analysis import get_clean_pairs
        import pandas as pd
        pairs, _, _ = get_clean_pairs()
        if pairs:
            df = pd.DataFrame(pairs)
            sd = df[df['symbol'] == symbol]
            total_wr = (df['result'] == 'win').mean() * 100 if len(df) > 0 else 0
            sym_wr = (sd['result'] == 'win').mean() * 100 if len(sd) > 0 else 0
            avg_hold_win = sd[sd['result'] == 'win']['hold_hours'].mean() if len(sd[sd['result'] == 'win']) > 0 else 0
            avg_hold_loss = sd[sd['result'] == 'loss']['hold_hours'].mean() if len(sd[sd['result'] == 'loss']) > 0 else 0
            win_df = df[df['result'] == 'win']
            loss_df = df[df['result'] == 'loss']
            avg_win_pnl = win_df['pnl_pct_after_fee'].mean() if len(win_df) > 0 else 0
            avg_loss_pnl = loss_df['pnl_pct_after_fee'].mean() if len(loss_df) > 0 else 0
            h2_summary = (
                f"全体勝率: {total_wr:.0f}% ({len(df)}件), "
                f"{symbol}勝率: {sym_wr:.0f}% ({len(sd)}件), "
                f"平均Win: {avg_win_pnl:+.2f}%, 平均Loss: {avg_loss_pnl:+.2f}%, "
                f"Win保有: {avg_hold_win:.0f}h, Loss保有: {avg_hold_loss:.0f}h"
            )
    except Exception as e:
        h2_summary = f"H.2データ取得失敗: {e}"

    # 2. EvolveRルール
    evolver_summary = ""
    try:
        adj_path = "vault/evolver/scoring_adjustments.json"
        if os.path.exists(adj_path):
            with open(adj_path, encoding='utf-8') as f:
                adj_data = json.load(f)
            rules = adj_data.get("adjustments", [])
            evolver_summary = "; ".join(
                f"{r['rule_id']}: {r['adjustment']:+d} ({r['evidence']})"
                for r in rules
            )
    except Exception:
        pass

    # --- F5: マクロ資本フローデータ読み込み ---
    macro_context = ""
    try:
        macro_path = "vault/blackboard/macro_flow.json"
        if os.path.exists(macro_path):
            with open(macro_path, encoding="utf-8") as f:
                macro_flow = json.load(f)
            md = macro_flow.get("macro_data", {})
            if md and "spy" in md and not md["spy"].get("error"):
                spy = md.get("spy", {})
                dxy = md.get("dxy", {})
                gold = md.get("gold", {})
                us10y = md.get("us10y", {})
                btc_dom = md.get("btc_dominance", {})
                macro_context = (
                    f"S&P500(SPY): {spy.get('value','?')} (1d:{spy.get('change_1d','?')}%, 7d:{spy.get('change_7d','?')}%, 30d:{spy.get('change_30d','?')}%)\n"
                    f"ドル指数(DXY): {dxy.get('value','?')} (1d:{dxy.get('change_1d','?')}%, 7d:{dxy.get('change_7d','?')}%, 30d:{dxy.get('change_30d','?')}%)\n"
                    f"ゴールド(GC=F): {gold.get('value','?')} (1d:{gold.get('change_1d','?')}%, 7d:{gold.get('change_7d','?')}%, 30d:{gold.get('change_30d','?')}%)\n"
                    f"米10年債利回り(TNX): {us10y.get('value','?')} (1d:{us10y.get('change_1d','?')}%, 7d:{us10y.get('change_7d','?')}%, 30d:{us10y.get('change_30d','?')}%)\n"
                    f"BTC Dominance: {btc_dom.get('value','?')}%"
                )
    except Exception as e:
        macro_context = f"マクロデータ取得失敗: {e}"

    # --- LLM戦略評価 ---
    prompt = f"""あなたは自律取引AIエージェントNeoの「分析官」だ。
あなたはトレーダーではない。BUY/SELLの推奨はするな。
マクロ環境のフェーズ分類と、リスク・機会要因の列挙のみを行え。

【評価対象】
{symbol} @ ${current_price:.6f}
センチメント: {sentiment_label} ({sentiment_score:.2f})
バックテスト信頼度: {bt_confidence}

【H.2統計分析】
{h2_summary}

【EvolveR自動ルール】
{evolver_summary or "ルールなし"}

【直近の失敗パターン】
{failure_summary}

【BTC市場コンテキスト】
{btc_context if btc_context else "データなし"}

【マクロ資本フローデータ（お盆フレームワーク）】
{macro_context if macro_context else "データなし"}

【お盆フレームワーク — 資本ローテーション解釈ガイド】
資金（ビー玉）はリスクカーブに沿って流れる。仮想通貨はリスクカーブの末端（最後に入り、最初に抜ける）。
5指標から「お盆の傾き」を読み取り、以下の4フェーズのどれに該当するか判定せよ:

Phase 1: RISK_OFF_ACCUMULATE（仕込み時）
  株式上昇+DXY下降+Gold横ばい+US10Y下降+BTC Dom安定 → 仮想通貨は割安

Phase 2: RISK_ON_RIDE（上昇局面）
  株式上昇+仮想通貨上昇+BTC Dom低下（アルト加速）→ 流入中

Phase 3: RISK_ON_DISTRIBUTE（利確検討）
  BTC Dom急落+アルト急騰+Gold下降+DXY下降 → 過熱サイン

Phase 4: RISK_OFF_EXIT（撤退局面）
  株式下降+DXY上昇+Gold上昇+US10Y上昇+BTC全面安 → 資金流出中

指標が混在する場合は最も近いフェーズを選べ。判断不能ならRISK_ON_RIDEを返せ。

【過去の教訓】
{formatted_precedents[:500]}

以下のJSON形式のみで回答せよ（余計なテキスト不可）:
{{"risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
"risk_factors": ["リスク要因（最大5つ・各20字以内）"],
"opportunity_factors": ["機会要因（最大3つ・各20字以内）"],
"capital_flow_phase": "RISK_OFF_ACCUMULATE/RISK_ON_RIDE/RISK_ON_DISTRIBUTE/RISK_OFF_EXIT",
"macro_summary": "マクロ環境の要約（30字以内）",
"worst_case": "最悪シナリオ（30字以内）",
"mitigation": "対策（30字以内）",
"reasoning": "根拠（50字以内）"}}"""

    default_result = {
        "risk_level": "MEDIUM",
        "risk_factors": [],
        "opportunity_factors": [],
        "capital_flow_phase": "RISK_ON_RIDE",
        "macro_summary": "データなし",
        "worst_case": "不明",
        "mitigation": "標準SL",
        "reasoning": "評価失敗・デフォルト",
    }

    try:
        model = ModelFactory.get_genai_model("fast")
        resp = model.generate_content(prompt)
        raw = resp.text.strip()
        # JSON抽出
        clean = raw
        if "```" in clean:
            clean = clean.split("```")[1].replace("json", "", 1).strip()
        if "{" in clean:
            clean = clean[clean.index("{"):clean.rindex("}")+1]
        parsed = json.loads(clean)
        # 安全制限: capital_flow_phaseの検証
        valid_phases = {"RISK_OFF_ACCUMULATE", "RISK_ON_RIDE", "RISK_ON_DISTRIBUTE", "RISK_OFF_EXIT"}
        if parsed.get("capital_flow_phase") not in valid_phases:
            parsed["capital_flow_phase"] = "RISK_ON_RIDE"
        if not parsed.get("macro_summary"):
            parsed["macro_summary"] = "不明"
        print(f"  🎯 [Phase 1e] リスク={parsed['risk_level']}, phase={parsed['capital_flow_phase']}, macro={parsed['macro_summary']}")
        return parsed
    except json.JSONDecodeError:
        print(f"  ⚠️ [Phase 1e] JSONパース失敗、フォールバック")
        return default_result
    except Exception as e:
        print(f"  ⚠️ [Phase 1e] 戦略評価失敗: {str(e)[:60]}")
        return default_result


if __name__ == '__main__':
    result = run_strategic_assessment(
        symbol="VIRTUAL", current_price=0.64,
        sentiment_score=-0.40, sentiment_label="bearish",
        bt_confidence="HIGH",
        formatted_precedents="過去の記録なし。",
        failure_summary="失敗パターンデータなし"
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
