"""
PlanningCrew — 戦略リスク評価エージェント (Phase 1e)

Neo内部データ（H.2統計、EvolveRルール、ChromaDB記憶、scoring_adjustments）を
統合し、構造化されたリスク評価を出力する。

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
                              failure_summary: str = "") -> dict:
    """
    内部データに基づく戦略リスク評価を実行。
    
    Returns:
        dict with keys:
        - risk_level: "LOW" / "MEDIUM" / "HIGH" / "CRITICAL"
        - risk_factors: list of str (最大5つ)
        - opportunity_factors: list of str (最大3つ)
        - recommended_position_pct: 0-10 (推奨ポジションサイズ%)
        - worst_case: str (最悪シナリオ)
        - mitigation: str (対策)
        - confidence_modifier: int (-15 to +15)
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

    # --- LLM戦略評価 ---
    prompt = f"""あなたは自律取引AIエージェントNeoの戦略リスク評価モジュールだ。

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

【過去の教訓】
{formatted_precedents[:500]}

以下のJSON形式のみで回答せよ（余計なテキスト不可）:
{{"risk_level": "LOW/MEDIUM/HIGH/CRITICAL",
"risk_factors": ["リスク要因（最大5つ・各20字以内）"],
"opportunity_factors": ["機会要因（最大3つ・各20字以内）"],
"recommended_position_pct": 0から10の整数,
"worst_case": "最悪シナリオ（30字以内）",
"mitigation": "対策（30字以内）",
"confidence_modifier": -15から+15の整数,
"reasoning": "根拠（50字以内）"}}"""

    default_result = {
        "risk_level": "MEDIUM",
        "risk_factors": [],
        "opportunity_factors": [],
        "recommended_position_pct": 5,
        "worst_case": "不明",
        "mitigation": "標準SL",
        "confidence_modifier": 0,
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
        # 安全制限
        parsed["confidence_modifier"] = max(-15, min(15, int(parsed.get("confidence_modifier", 0))))
        parsed["recommended_position_pct"] = max(0, min(10, int(parsed.get("recommended_position_pct", 5))))
        print(f"  🎯 [Phase 1e] リスク={parsed['risk_level']}, conf_mod={parsed['confidence_modifier']:+d}, pos={parsed['recommended_position_pct']}%")
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
