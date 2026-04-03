# 📐 F5: お盆フレームワーク — 資本ローテーション解釈レイヤー設計書

> **作成日**: 2026/04/03
> **ステータス**: 設計完了・実装待ち
> **前提**: F1(exit_profile) + F2(BTC急落リスク) 完了済み

---

## 1. 課題

現在のNeoはニュースを FinBERT → sentiment スコア に変換しているだけ。
「FRBが利下げ示唆」も「関税強化」も、仮想通貨の文脈での感情極性しか見ない。

**欠けているもの**:
- 「なぜBTCが下がっているか」（資金がどこに逃げたか）
- 「いつ仮想通貨に資金が戻るか」（お盆の傾きの方向）
- 「今は仕込み時か利確時か」（資本ローテーションの段階）

お盆メタファー: ビー玉（資金）は株式→仮想通貨の順に流れ、
逆順（仮想通貨→株式→債券/ゴールド/現金）に引き上げられる。
仮想通貨はリスクカーブの末端（最後に入り、最初に抜ける）。

---

## 2. 見るべき5指標

| 指標 | 意味 | データソース | コスト |
|---|---|---|---|
| S&P500 (SPY) | 株式への資金集中度 | Yahoo Finance API (yfinance) | 無料 |
| DXY (ドル指数) | 現金への退避度 | Yahoo Finance API (DX-Y.NYB) | 無料 |
| Gold (XAU) | 安全資産への逃避度 | Yahoo Finance API (GC=F) | 無料 |
| US10Y (米10年債利回り) | FRB緩和/引締の方向 | Yahoo Finance API (^TNX) | 無料 |
| BTC Dominance | 仮想通貨内ローテーション段階 | CoinGecko API (無料枠) | 無料 |

---

## 3. 資本フロー4フェーズ

Phase 1: RISK_OFF_ACCUMULATE（仕込み時）
  お盆の状態: 株式/ゴールド/債券に傾斜 → 仮想通貨は割安
  指標シグナル: S&P500上昇 + DXY下降 + Gold横ばい + US10Y下降 + BTC Dom安定
  Neoの行動: BUY confidence +5〜+10、長期戦略(macro_value等)を優先

Phase 2: RISK_ON_RIDE（上昇局面に乗る）
  お盆の状態: リスク選好拡大 → 仮想通貨にビー玉が流入中
  指標シグナル: S&P500上昇 + 仮想通貨上昇 + BTC Dom低下（アルト加速）
  Neoの行動: 通常判断、トレンドフォロー戦略を優先

Phase 3: RISK_ON_DISTRIBUTE（利確検討）
  お盆の状態: 仮想通貨に過剰に傾斜 → 過熱サイン
  指標シグナル: BTC Dom急落 + アルト急騰 + Gold下降 + DXY下降
  Neoの行動: BUY confidence -5〜-10、トレーリング利確を引き締め

Phase 4: RISK_OFF_EXIT（撤退局面）
  お盆の状態: リスク回避 → 仮想通貨から資金流出中
  指標シグナル: S&P500下降 + DXY上昇 + Gold上昇 + US10Y上昇 + BTC全面安
  Neoの行動: BUY confidence -10〜-15、既存ポジションのSL引き締め

---

## 4. アーキテクチャ

[neo-collector.service に追加]
  日次(JST 02:00) → macro_collector.py
                      - yfinance: SPY, DX-Y.NYB, GC=F, ^TNX (日足)
                      - CoinGecko: BTC Dominance
                      - vault/blackboard/macro_flow.json に保存

[trinity_council.py Phase 1e]
  Planning Agent呼び出し時
    - 既存: btc_context, sentiment, H.2統計, failure_summary
    - 追加: macro_flow データ（5指標 + 変動率）
    - 追加: お盆フレームワーク解釈プロンプト

[Planning Agentの出力に追加]
  既存: risk_level, confidence_modifier, risk_factors, ...
  追加:
    capital_flow_phase: RISK_OFF_ACCUMULATE | RISK_ON_RIDE |
                        RISK_ON_DISTRIBUTE | RISK_OFF_EXIT
    macro_summary: str (30字以内のマクロ環境要約)

[Phase 4b スコアリング]
  capital_flow_phase → confidence修正値
    RISK_OFF_ACCUMULATE: +5
    RISK_ON_RIDE: +0 (通常判断)
    RISK_ON_DISTRIBUTE: -5
    RISK_OFF_EXIT: -10

---

## 5. 実装ステップ

### Step 1: マクロデータ収集 (tools/macro_collector.py 新規作成)
- yfinance で SPY, DX-Y.NYB, GC=F, ^TNX の30日分日足を取得
- CoinGecko /global で BTC Dominance を取得
- 各指標の現在値 + 1d/7d/30d変動率を計算
- vault/blackboard/macro_flow.json の macro_data フィールドに保存

### Step 2: neo-collector.service 日次バッチ組込み
- 既存の日次パージの直後にmacro_collector.collect_macro_data()を呼び出し
- 失敗時はスキップ（既存データを維持）

### Step 3: Planning Agent プロンプト拡張
- macro_flow.json からmacro_dataを読み込み
- お盆フレームワーク解釈プロンプトを追加
  - 5指標の意味と読み方を明記
  - 4フェーズの定義と判定基準を明記
- 出力JSONにcapital_flow_phaseとmacro_summaryを追加

### Step 4: Phase 4b スコアリング統合
- capital_flow_phaseに基づくconfidence修正値を追加
- 既存のPlanning ±10クランプ内には含めない（別枠で±10制限）
- ログにmacro_labelを追加

### Step 5: テスト・検証
- macro_collector手動実行 → データ取得確認
- Planning Agent手動テスト → capital_flow_phase出力確認
- Phase 4bログでmacro_labelが表示されることを確認

---

## 6. 安全装置

| 装置 | 仕様 |
|---|---|
| macro_data取得失敗時 | Planning Agentは既存ロジックのみで動作 |
| capital_flow_phase不明時 | 修正値0（通常判断） |
| yfinance API制限 | 日次1回のみ取得、Blackboardにキャッシュ |
| macro confidence修正上限 | ±10（Planning修正とは別枠） |
| CoinGecko API制限 | 日次1回、レート制限10-30回/分（十分） |

---

## 7. データ取得の現実確認

| 指標 | yfinanceティッカー | 確認事項 |
|---|---|---|
| S&P500 | SPY (ETF) | 米国市場時間のみ更新。土日は前日終値 |
| DXY | DX-Y.NYB | 流動性低め。代替: UUP (ETF) |
| Gold | GC=F (先物) | 24h取引。代替: GLD (ETF) |
| US10Y | ^TNX | 利回り。米国市場時間のみ |
| BTC Dom | CoinGecko /global | 24h更新。レート制限あり |

→ pip install yfinance が必要（neo-env内）

---

## 8. 既存macro_flow.jsonとの関係

現在 vault/blackboard/macro_flow.json にはFear & Greedベースの
score/regimeが入っている。これを拡張する形でmacro_dataを追加。
既存のcfr（macro_flow score）ロジックは維持。

---

## 9. 実装順序と工数

| Step | 内容 | 工数 | 依存 |
|---|---|---|---|
| S1 | yfinance導入 + macro_collector.py新規作成 | 小 | なし |
| S2 | neo-collector.service日次バッチに組込み | 小 | S1 |
| S3 | planning_agent.pyプロンプト拡張 + capital_flow_phase出力 | 中 | S2 |
| S4 | Phase 4bスコアリング統合 | 小 | S3 |
| S5 | テスト + 手動実行 → Phase 1eの出力検証 | 小 | S4 |

全体工数: 1〜2セッション

---

## 10. 期待される効果

| 現在 | F5実装後 |
|---|---|
| BTC -45%を「下落」としか解釈できない | 「株式に資金集中中→仮想通貨は割安→ACCUMULATE」と解釈 |
| ニュースの感情極性のみ | マクロ環境の構造的理解に基づく判断 |
| Planning confは市場恐怖に引きずられる | 資本フローのフェーズに基づく合理的な修正 |
| 常時plan -7〜-10 | ACCUMULATE時は+5、EXIT時のみ-10 |


---

## 11. LLMの役割再定義 — 分析官であり判断者ではない

### 背景（v6.5ag相関分析の発見）

LLM confidenceと実勝率が逆相関していた:
- conf 65-78: 勝率47%, avg PnL -1.5%
- conf 45-54: 勝率83%, avg PnL +2.2%

LLMが「BUYすべき」と確信するほど実際は負ける。
LLMに数値判断をさせるべきではない。

### 新方針

LLMにやらせること:
- ニュースのカテゴリ分類、影響先アセット判定
- お盆の傾き → 4フェーズ分類
- 失敗パターンの構造化分類(E1)
- 三者協議の議論過程

LLMにやらせないこと:
- sentiment → confidence変換
- confidence_modifier数値出力
- confidence_adjustment(E2)
- 最終verdictの信頼度

全ての数値判断はE3統計エンジンとPhase 4bルールに委ねる。

### Planning Agentプロンプトへの追記

- 「あなたは分析官であり、トレーダーではない」
- 「BUY/SELLの推奨はするな」
- 「マクロ環境のフェーズ分類と、リスク要因の列挙のみを行え」
- 「confidence_modifierは廃止。代わりにcapital_flow_phaseを出力せよ」

---

## 12. 教訓フローの再設計 — E1/E2/E3のマクロ統合

### 現在の教訓フロー（個別取引レベル）

負け取引 → E1(failure_category分類) → ChromaDB保存
         → E2(LLMがadj=+-10を出力) → Phase 4bに直接加算
         → E3(EvolveRが統計ルール生成) → Phase 4b自動反映

問題: E1の7カテゴリは実は同じ根本原因の症状かもしれない。
「trend_against」「btc_correlation」「bad_timing」は全て
「お盆が仮想通貨から傾いているのに買った」の異なる現れ方。

### 新しい教訓フロー（マクロフェーズレベル）

BUY時: entry_contextにcapital_flow_phaseを保存
SELL時: E1構造化内省にcapital_flow_phaseを含める
Nightly Batch: E3がフェーズ別勝率を自動集計
  → scoring_adjustments.jsonに condition.type="capital_flow_phase" を追加
  → 例: RISK_OFF_EXIT期のBUY → 勝率30% → adjustment=-10
  → 例: RISK_OFF_ACCUMULATE期のBUY → 勝率80% → adjustment=+5

### E2の段階的移行

F5実装直後: E2維持（フェーズ別勝率データが未蓄積）
フェーズ別15件以上: adj=0に固定、分析テキストのみ出力（E3統計ルールが代替）
フェーズ別30件以上: 廃止またはE3入力に変換（完全に統計駆動）

### E3 condition.type追加

scoring_adjustments.jsonに新しい条件タイプを追加:
  condition.type="capital_flow_phase"
  match: RISK_OFF_ACCUMULATE | RISK_ON_RIDE | RISK_ON_DISTRIBUTE | RISK_OFF_EXIT
  評価方法: Planning Agentの最新出力（Blackboard経由）と照合

Phase 4bの条件マッチングに追加:
  elif _ctype == "capital_flow_phase":
      _current_phase = _planning_result.get("capital_flow_phase", "")
      _matched = (_cond.get("match") == _current_phase)

---

## 13. 実装ステップ（更新版）

S1: yfinance導入 + macro_collector.py新規作成 (小)
S2: neo-collector.service日次バッチに組込み (小)
S3: planning_agent.pyプロンプト拡張 — 分析官方針+お盆FW+capital_flow_phase出力 (中)
S3b: planning_agent.pyからconfidence_modifier廃止 → capital_flow_phaseに置換 (小)
S4: Phase 4bスコアリング統合 — capital_flow_phase → macro_adj (小)
S5: BUY時entry_contextにcapital_flow_phase保存 (小)
S6: E3にcapital_flow_phase条件タイプ追加 (小)
S7: テスト + 手動実行 → Phase 1eの出力検証 (小)
S8: E2段階的移行 — データ蓄積後 (15件以上蓄積後)

全体工数: 2-3セッション

---

## 14. 期待される効果（更新版）

マクロ環境理解: BTC価格のみ → S&P500/DXY/Gold/US10Y/BTC Dom
ニュース解釈: FinBERT感情極性のみ → LLMがマクロ文脈で構造的に解釈
教訓の抽象度: 7カテゴリ（症状レベル） → 4フェーズ（根本原因レベル）
LLMの役割: 分析+判断を兼任 → 分析のみ（判断は統計エンジン）
E2 adjustment: LLMが+-10を直接出力 → 統計ルール(E3)が自動導出
Planning conf: 常時-7〜-10 → フェーズ依存（+5〜-10）
取引判断の根拠: 「LLMが自信あり」 → 「マクロフェーズX期の勝率がY%」
