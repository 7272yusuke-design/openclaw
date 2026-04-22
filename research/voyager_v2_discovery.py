"""
Voyager V2 Phase A — 発見層（Discovery Layer）
設計書: docs/v2_voyager_design.md §1 発見層
"""
import sys; sys.path.insert(0, '.')
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

MIN_SAMPLE_SIZE = 5
MAX_HYPOTHESES = 5
LOOKBACK_DAYS = 30
WIN_RATE_DIVERGENCE_PP = 15
LLM_VS_ACTUAL_TOL_PP = 10
OUTPUT_JSON_PATH = "vault/voyager/hypothesis.json"
CHROMA_CATEGORY = "voyager_hypothesis"


def _jst_hour(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=9))).hour
    except Exception:
        return -1


def _dow(ts_str):
    try:
        dt = datetime.fromisoformat(ts_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=9))).weekday()
    except Exception:
        return -1


def _categorize_sell_reason(reason):
    r = (reason or "").lower()
    if "stop loss" in r or "損切" in r: return "stop_loss"
    if "rsi" in r: return "rsi_exit"
    if "trailing" in r or "trail" in r: return "trailing"
    if "time" in r or "時間" in r: return "time_exit"
    if "strategy bear" in r or "bear stage" in r: return "strategy_bear"
    if "strategy bull" in r or "bull stage" in r: return "strategy_bull"
    return "other"


def build_discovery_dataset(days=LOOKBACK_DAYS):
    from research.h2_trade_analysis import get_clean_pairs
    pairs, _, _ = get_clean_pairs()
    if not pairs:
        return [], 0.0, 0
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    filtered = []
    for p in pairs:
        try:
            buy_dt = datetime.fromisoformat(p.get("buy_ts", ""))
            if buy_dt.tzinfo is None:
                buy_dt = buy_dt.replace(tzinfo=timezone.utc)
            if buy_dt >= cutoff:
                filtered.append(p)
        except Exception:
            continue
    if not filtered:
        return [], 0.0, 0
    dataset = []
    for p in filtered:
        dataset.append({
            "symbol": p.get("symbol", ""),
            "buy_hour": _jst_hour(p.get("buy_ts", "")),
            "buy_dow": _dow(p.get("buy_ts", "")),
            "strategy_tag": p.get("strategy_tag", ""),
            "sell_reason_category": _categorize_sell_reason(p.get("sell_reason", "")),
            "hold_hours": round(float(p.get("hold_hours", 0)), 1),
            "pnl_pct_after_fee": round(float(p.get("pnl_pct_after_fee", 0)), 2),
            "result": p.get("result", ""),
        })
    wins = sum(1 for d in dataset if d["result"] == "win")
    overall_wr = (wins / len(dataset)) * 100 if dataset else 0.0
    return dataset, overall_wr, len(dataset)


def _build_prompt(dataset, overall_wr):
    dataset_json = json.dumps(dataset, ensure_ascii=False, separators=(",", ":"))
    return f"""あなたは仮想通貨取引のパターン発見エージェントです。過去の決済履歴から、統計的に偏りのある「隠れた勝ちパターン」または「避けるべき負けパターン」を発見してください。

【決済履歴データ】{len(dataset)}件
全体勝率: {overall_wr:.1f}%
フィールド定義:
- symbol: 銘柄
- buy_hour: BUY時刻のJST時間(0-23)
- buy_dow: BUY日の曜日(0=月,1=火,...,6=日)
- strategy_tag: 採用戦略(atr_breakout, macd_cross等)
- sell_reason_category: 出口タイプ(stop_loss, rsi_exit, trailing, time_exit, strategy_bear, strategy_bull, other)
- hold_hours: 保有時間
- pnl_pct_after_fee: 手数料後損益率(%)
- result: win または loss

データ:
{dataset_json}

【既存スキル(重複提案禁止)】
- asia/eu/us_session_pattern (時間帯3分割のみ)
- stop_loss/rsi/trailing/time_exit_pattern (出口タイプ単独)
- virtual/eth/btc_trade_pattern (単一銘柄単独)

【発見タスク】
既存スキルと異なる視点で、勝率が全体({overall_wr:.1f}%)から{WIN_RATE_DIVERGENCE_PP}pp以上乖離する条件を最大{MAX_HYPOTHESES}個発見してください。既存スキルより具体的な「複数条件のAND組合せ」で、統計的に検証可能であること。

【必須制約】
- 各パターンは以下を満たす:
  - サンプル数 >= {MIN_SAMPLE_SIZE}件
  - 閾値が明示的 (例: "hold_hours<24" "strategy_tag=atr_breakout AND buy_hour in [0,1,2,3,4,5,6,7,8]")
  - 曖昧な表現(「よく動く時」「急落時」等)は禁止
- 仮説(hypothesis)はなぜその条件で偏るかを1文で

【出力形式】
以下のJSON配列**のみ**。説明文・markdown・前置き後置きなし。

[
  {{
    "name": "atr_breakout_asia_session",
    "condition_text": "strategy_tag=atr_breakout AND buy_hour in [0..8]",
    "condition_logic": {{
      "AND": [
        {{"field": "strategy_tag", "op": "eq", "value": "atr_breakout"}},
        {{"field": "buy_hour", "op": "in", "value": [0,1,2,3,4,5,6,7,8]}}
      ]
    }},
    "sample_size": 7,
    "win_rate": 85.7,
    "hypothesis": "アジア時間はボラが低く、ブレイクアウトがダマシになりにくいため"
  }}
]
"""


def _extract_json_array(text):
    if not text:
        return None
    fence = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if fence:
        return fence.group(1)
    s = text.find("[")
    e = text.rfind("]")
    if s >= 0 and e > s:
        return text[s:e + 1]
    return None


def call_llm_discovery(dataset, overall_wr):
    if not dataset:
        return []
    try:
        from core.model_factory import ModelFactory
        model = ModelFactory.get_genai_model("critical")
        prompt = _build_prompt(dataset, overall_wr)
        response = model.generate_content(prompt)
        text = ""
        if hasattr(response, "text"):
            text = response.text
        elif hasattr(response, "candidates"):
            for c in response.candidates:
                if hasattr(c, "content") and hasattr(c.content, "parts"):
                    for p in c.content.parts:
                        if hasattr(p, "text"):
                            text += p.text
        else:
            text = str(response)
        json_str = _extract_json_array(text)
        if not json_str:
            print(f"⚠️ [VoyagerV2] JSON抽出失敗: {text[:200]}")
            return []
        h = json.loads(json_str)
        if not isinstance(h, list):
            return []
        return h
    except Exception as e:
        print(f"⚠️ [VoyagerV2] LLM失敗: {e}")
        return []


def _eval_condition(logic, record):
    if not isinstance(logic, dict):
        return False
    if "AND" in logic:
        return all(_eval_condition(c, record) for c in logic["AND"])
    if "OR" in logic:
        return any(_eval_condition(c, record) for c in logic["OR"])
    field = logic.get("field")
    op = logic.get("op")
    value = logic.get("value")
    if field is None or field not in record:
        return False
    rv = record[field]
    try:
        if op == "eq": return rv == value
        if op == "ne": return rv != value
        if op == "lt": return float(rv) < float(value)
        if op == "le": return float(rv) <= float(value)
        if op == "gt": return float(rv) > float(value)
        if op == "ge": return float(rv) >= float(value)
        if op == "in": return rv in value
        if op == "contains": return str(value).lower() in str(rv).lower()
    except Exception:
        return False
    return False


def validate_hypothesis(h, dataset):
    res = {"accepted": False, "reject_reason": "", "actual_sample_size": 0, "actual_win_rate": 0.0}
    for fld in ("name", "condition_logic", "sample_size", "win_rate", "hypothesis"):
        if fld not in h:
            res["reject_reason"] = f"フィールド欠落: {fld}"
            return res
    matched = [d for d in dataset if _eval_condition(h["condition_logic"], d)]
    actual_n = len(matched)
    if actual_n == 0:
        res["reject_reason"] = "条件合致0件"
        return res
    actual_wins = sum(1 for d in matched if d["result"] == "win")
    actual_wr = (actual_wins / actual_n) * 100
    res["actual_sample_size"] = actual_n
    res["actual_win_rate"] = round(actual_wr, 1)
    if actual_n < MIN_SAMPLE_SIZE:
        res["reject_reason"] = f"サンプル不足 {actual_n}<{MIN_SAMPLE_SIZE}"
        return res
    llm_n = int(h.get("sample_size", 0))
    llm_wr = float(h.get("win_rate", 0))
    if abs(actual_n - llm_n) > max(2, llm_n * 0.3):
        res["reject_reason"] = f"サンプル数乖離 LLM={llm_n} 実={actual_n}"
        return res
    if abs(actual_wr - llm_wr) > LLM_VS_ACTUAL_TOL_PP:
        res["reject_reason"] = f"勝率乖離 LLM={llm_wr:.1f} 実={actual_wr:.1f}"
        return res
    res["accepted"] = True
    return res


def save_to_chromadb(validated_items):
    try:
        from core.memory_db import NeoMemoryDB
        mem = NeoMemoryDB()
        try:
            existing = mem.collection.get(where={"category": CHROMA_CATEGORY}, include=[])
            old_ids = existing.get("ids", []) if existing else []
            if old_ids:
                mem.delete(old_ids)
                print(f"🧹 [VoyagerV2] 旧hypothesis {len(old_ids)}件削除")
        except Exception as e:
            print(f"⚠️ [VoyagerV2] 旧削除失敗（続行）: {e}")
        saved = 0
        for item in validated_items:
            h = item["hypothesis"]
            v = item["validation"]
            doc_text = (f"Voyager Hypothesis [{h['name']}]: {h.get('condition_text','')}\n"
                        f"実サンプル={v['actual_sample_size']}件 実勝率={v['actual_win_rate']}%\n"
                        f"仮説: {h.get('hypothesis','')}")
            metadata = {
                "source": "voyager_v2_discovery",
                "category": CHROMA_CATEGORY,
                "tier": "3",
                "tag": f"voyager_hypothesis,{h['name']}",
                "actual_win_rate": str(v["actual_win_rate"]),
                "actual_sample_size": str(v["actual_sample_size"]),
                "status": "hypothesis",
            }
            mem.store(doc_text, metadata=metadata)
            saved += 1
        return saved
    except Exception as e:
        print(f"⚠️ [VoyagerV2] ChromaDB保存失敗: {e}")
        return 0


def save_to_json_backup(validated_items, overall_wr, pair_count):
    try:
        Path(os.path.dirname(OUTPUT_JSON_PATH)).mkdir(parents=True, exist_ok=True)
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "overall_win_rate": round(overall_wr, 1),
            "pair_count": pair_count,
            "hypotheses": [{**it["hypothesis"], "_validation": it["validation"]} for it in validated_items],
        }
        with open(OUTPUT_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"💾 [VoyagerV2] JSON保存: {OUTPUT_JSON_PATH}")
    except Exception as e:
        print(f"⚠️ [VoyagerV2] JSON保存失敗: {e}")


def run_voyager_v2_discovery(dry_run=False):
    print(f"🚀 [VoyagerV2] 発見層開始 (dry_run={dry_run})")
    dataset, overall_wr, pair_count = build_discovery_dataset(days=LOOKBACK_DAYS)
    if pair_count < 10:
        print(f"⚠️ データ不足 {pair_count}<10: スキップ")
        return {"status": "skipped", "pair_count": pair_count}
    print(f"📊 {pair_count}ペア / 全体勝率{overall_wr:.1f}%")
    raw = call_llm_discovery(dataset, overall_wr)
    if not raw:
        return {"status": "no_hypotheses", "pair_count": pair_count}
    print(f"💡 LLM発見: {len(raw)}件")
    validated = []
    rejected = 0
    for h in raw:
        v = validate_hypothesis(h, dataset)
        if v["accepted"]:
            validated.append({"hypothesis": h, "validation": v})
            print(f"  ✅ {h.get('name')}: 実{v['actual_sample_size']}件 実勝率{v['actual_win_rate']}%")
        else:
            rejected += 1
            print(f"  ❌ {h.get('name','(no name)')}: {v['reject_reason']}")
    chroma_saved = 0
    if not dry_run:
        chroma_saved = save_to_chromadb(validated)
        save_to_json_backup(validated, overall_wr, pair_count)
    else:
        print("🧪 dry_run: 保存スキップ")
    return {
        "status": "ok", "pair_count": pair_count, "overall_win_rate": round(overall_wr, 1),
        "raw_count": len(raw), "validated_count": len(validated),
        "rejected_count": rejected, "chroma_saved": chroma_saved, "dry_run": dry_run,
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-llm", action="store_true")
    args = parser.parse_args()
    if args.no_llm:
        ds, wr, n = build_discovery_dataset()
        print(f"📊 {n}ペア / 全体勝率{wr:.1f}%")
        if ds:
            print(f"  サンプル1件目: {json.dumps(ds[0], ensure_ascii=False)}")
    else:
        run_voyager_v2_discovery(dry_run=args.dry_run)
