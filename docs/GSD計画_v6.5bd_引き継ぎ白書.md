# GSD計画 v6.5bd 引き継ぎ白書

- 更新日時: 2026/04/21 JST
- セッション: v6.5bd（LLM 429対策 — 全LLM呼び出しOpenRouter統一+コスト削減）
- 自己採点: 9/10（取引停止の根本原因特定・解決、副次バグ修正、コスト構造改善）

---

## 🎯 本セッションの主要成果

### 🥇 LLM 429 Rate Limit 問題の根本解決
- **問題**: 全LLM呼び出しがGemini無料枠の直接APIに殺到 → 429 RESOURCE_EXHAUSTED → Council常時タイムアウト → 強制WAIT → 取引停止
- **原因**: 3ルートすべてがGemini直接API一本だった
  - CrewAI (Bull/Bear/Neo): `ChatGoogleGenerativeAI` ハードコード
  - genai SDK (Phase 3b/E1/Reflexion/Planning): `ModelFactory.get_genai_model()` → Gemini直接
  - litellm (Scout/Moltbook): `gemini/gemini-2.0-flash` → Gemini直接
- **解決**:
  - ModelFactory に `get_crewai_llm()` 追加 — OpenRouter経由(litellm)でCrewAI GeminiCompletion回避
  - `_to_openrouter_id()` でモデル名→OpenRouter ID変換（gemini-2.0-flash → gemini-2.0-flash-001）
  - litellm.fallbacks で gemini-2.0-flash-001 ⇔ gemini-2.5-flash 自動切替
  - `_GenaiModelWrapper` に429リトライ(2回)+OpenRouterフォールバック追加
  - trinity_council: pro_model/flash_model を `ModelFactory.get_crewai_llm()` 経由に変更
  - scout_agent: ハードコードモデルを `ModelFactory.get_crewai_llm()` に変更
  - moltbook_tool/engager: `gemini/gemini-2.0-flash` → `openrouter/google/gemini-2.0-flash-001` に変更（7箇所）

### 🥈 LLMコスト構造の改善
- **問題**: Council 37回/日 × Moltbook投稿(LLM 2〜3回) = 約70〜100回の無駄なLLM呼び出し
- WAIT判定(全体の9割以上)でもMoltbook投稿していた
- **解決**: Phase 6 Moltbook投稿をBUY/SELL時のみに限定、WAIT時はスキップ
- **効果**: Moltbook起因のLLM呼び出しが約90%削減

### 🥉 APIキー不整合の修正
- moltbook_tool/engager で OpenRouterモデルに `GEMINI_API_KEY` を渡していた不具合を修正
- 全箇所を `OPENROUTER_API_KEY` に統一（6箇所）

### 副次バグ修正: ボラティリティ監視エラー
- `cannot access local variable 'get_latest_price_from_db'` — 30秒ごとのログ汚染
- Python 3.12のスコープ問題 → ローカルimport追加で解消

---

## 🔴 現状数値

| 項目 | 値 |
|---|---|
| 勝率(PaperWallet FIFO) | 75.8% (33ペア決済) |
| USDC | $79,258.82 |
| Holdings | BTC(0.1177) |
| Evaluator 決済済み | 85件 | 勝率 51.76% |
| Evaluator MaxDD | −26.0% |
| Sortino | 8.341 |

> ⚠️ PaperWallet FIFOとEvaluatorの勝率が乖離している（75.8% vs 51.76%）。Evaluator側はBUY単位FIFOペア分解カウント（別単位）のため。v6.5bb白書の分析を参照。

## サービス稼働状況
- neo-radar: active（429エラーなし）
- neo-collector: active
- neo-resource-api: active
- neo-acp-seller: active

---

## ⏭️ 次セッションの作業(優先順)

### 🥇 v6.5bc/bd 改修の効果観察
v6.5bcで自己進化機構を修復、v6.5bdで429を解消した。実際に取引が進んで効果が見えるまで1〜3日待つ必要がある。

1. **Council がBUY/SELL判断を出せるようになったか** — 429解消後、初のBUY判断を確認
2. E1プロンプト拡張: SL発火で failure_category='averaging_down' が出るか
3. ナンピン上限2: Phase 5ログに "🛑 BUY禁止" が出るか
4. Voyager: Nightly Batch後に6〜8件で安定するか
5. EvolveR: scoring_adjustments.json が健全な状態を維持するか

### 🥈 未着手: D. SL/TP 非対称性の設計見直し
- RR比 0.77 → 1.5+ に持ち上げる
- 観察後、E1の failure_category データを踏まえて判断

### 🥉 OpenRouter コスト監視
- Gemini無料枠→OpenRouter有料枠に移行したため、コスト推移を監視する必要がある
- CostGuard の spent は現在 $0.00（OpenRouter課金がCostGuardに連携されていない）
- OpenRouterダッシュボードで実コストを確認すること

### 🔧 中期: V2 自己進化層の実装
- Voyager V2 Phase A(発見層) 実装
- EvolveR V2 Phase A(観測集中化) 実装

### 📋 D3 移行ゲートの現実的見直し
- 構造問題は部分修復されたが、効果観察後に D3 条件見直しを再検討

---

## 🔒 前セッションから引き継ぐ情報(変更なし)

- ACP v2 seller runtime 実装・SSE接続完了(v6.5ba)
- DRY_RUN=true のまま稼働中(解除は本業改善優先のため保留)
- Graduation対応は棚上げ(Discord返答待ち)
- bt常時HIGH問題(v6.5ba から引き継ぎ、未解決)
- EXIT_PROFILES誤キー修正済み(v6.5ay)
- LEARNING_MODE dead path全削除済み(v6.5az)
- リセット前31件のChromaDB trade_result レコード残置(案α採用)

---

## 📁 本セッションで作成・変更したもの

| 種別 | 場所 | 内容 |
|---|---|---|
| 編集 | core/model_factory.py | get_crewai_llm(), _to_openrouter_id(), litellm fallbacks, _GenaiModelWrapper 429リトライ+フォールバック |
| 編集 | agents/trinity_council.py | pro_model/flash_model をModelFactory経由に変更, Phase 6 WAIT時Moltbookスキップ |
| 編集 | agents/scout_agent.py | ハードコードモデルをModelFactory.get_crewai_llm()に変更 |
| 編集 | tools/moltbook_tool.py | モデルID OpenRouter化(3箇所), APIキー OPENROUTER_API_KEY統一(3箇所) |
| 編集 | tools/moltbook_engager.py | モデルID OpenRouter化(4箇所), APIキー OPENROUTER_API_KEY統一(3箇所) |
| 編集 | run_trigger.py | ボラティリティ監視 get_latest_price_from_db ローカルimport追加 |
| 新規 | docs/GSD計画_v6.5bd_引き継ぎ白書.md | 本ファイル |

---

## LLM呼び出し構造（v6.5bd後）

| 呼び出し元 | ルート | モデル | 頻度 |
|---|---|---|---|
| Council Bull/Bear/Neo (CrewAI) | OpenRouter/litellm | gemini-2.0-flash-001 | 2h×3銘柄 |
| Phase 1d-R Reflexion (genai) | Gemini直接→429時OpenRouter | gemini-2.5-flash | Council毎 |
| Phase 3b 戦略書 (genai) | Gemini直接→429時OpenRouter | gemini-2.0-flash | BUY時のみ |
| Phase 6 Moltbook (litellm) | OpenRouter | gemini-2.0-flash-001 | **BUY/SELL時のみ(v6.5bd)** |
| SentimentCrew (CrewAI) | OpenRouter/litellm | gemini-2.0-flash-001 | Council毎 |
| ScoutCrew (CrewAI) | OpenRouter/litellm | gemini-2.5-flash | Council毎 |
| E1 内省 (genai) | Gemini直接→429時OpenRouter | gemini-2.5-flash | SELL時のみ |
| Planning (genai) | Gemini直接→429時OpenRouter | gemini-2.5-flash | Council毎 |
| Moltbook engager (litellm) | OpenRouter | gemini-2.0-flash-001 | 2h毎 |
