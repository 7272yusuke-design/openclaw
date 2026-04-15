# 📐 GSD計画 v6.5ax 引き継ぎ白書

> **更新日時**: 2026/04/15 JST
> **セッション**: v6.5ax（学習モード100件到達OFF + 勝率改善3施策）
> **自己採点**: 85/100（学習モードOFF・戦略ブラックリスト・スコアリング簡素化を完了）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率(FIFOロット) | **49.4%（77件決済: 38勝39敗）** ← 目標60%未達 |
| 勝率(SELL単位) | **71.4%（28ペア: 20勝8敗）** |
| ETH | 46.2%（39ロット） |
| VIRTUAL | 52.6%（38ロット） |
| USDC | $63,736.78 |
| Holdings | BTC(0.1177/long) / VIRTUAL(15515/short) / ETH(1.8674/short) |
| サービス | 全4サービス稼働中 |
| L4 DD | ~5% — 要注意圏 |
| Council | 1hローテーション: BTC → VIRTUAL → ETH |
| 学習モード | **OFF（107件到達 → 2026/04/15に切替完了）** |
| ACP Graduation | Stats API: 26件/100%成功 だがUI未表示（VP側バグ）→ Discord問い合わせ必要 |

---

## ✅ 本セッション完了タスク

### Task 1: 学習モードOFF
- `core/config.py` の `LEARNING_MODE = False` に変更
- 107件到達確認済み
- TP/SL幅が通常化（TP 7%→20%, SL 3%→10%）
- BUY促進ルール・Bear緩和が解除

### Task 2: STRATEGY_BLACKLIST導入（勝率改善）
- `core/config.py` に `STRATEGY_BLACKLIST` 追加
- `research/backtests/run_backtest.py` の `run_all_strategies` でフィルタ適用
- 除外対象（FIFOロット勝率）:
  - mean_reversion: 0/3 (0%)
  - macro_value: 6/17 (35.3%)
  - gplearn_evolved: 4/11 (36.4%)
- 残存戦略: atr_breakout(55%), macd_cross(100%), triple_ma_cross(100%), ichimoku_cloud, golden_cross, dca_accumulation

### Task 3: Phase 4bスコアリング簡素化（勝率改善）
- **sentiment scoring無効化**: FinBERTが慢性ネガティブ（-0.35〜+0.15）で常に-5/-10を付与、BUY判断を不当に抑制
- **reflexion scoring無効化**: E2が慢性マイナス（-10が頻出）でconfidenceを構造的に押し下げ
- 効果: confidence平均が50前後→55〜65に改善見込み

### Phase 4b スコアリング現構成（簡素化後）
| 要素 | 範囲 | 状態 |
|---|---|---|
| ニュートラル起点 | 50 | ✅ |
| bt (backtest) | +5〜+15 | ✅（ただし常にHIGH=+15で差がつかない） |
| acc (過去精度) | -5〜+10 | ✅ |
| TZ (時間帯) | ±3 | ✅ |
| npin (ナンピン) | -5 | ✅ |
| streak (連敗) | -5/-10 | ✅ |
| cfr (CFR) | -10〜+5 | ✅ |
| macro (F5) | -3〜+5 | ✅ |
| strat (戦略信頼度) | ±5 | ✅（現在は常に0） |
| evol (EvolveR) | ±15 | ✅（現在はほぼ0） |
| ~~sentiment~~ | ~~±10~~ | ❌ 無効化 |
| ~~reflexion~~ | ~~±10~~ | ❌ 無効化 |

---

## ⏭️ 次セッションの作業

### 最優先 — 効果モニタリング
1. 数日後にログで新confidence分布を確認（`grep 'Phase 4b.*ルールベース再計算' radar_output.log | tail -20`）
2. TP/SL幅通常化でL4 DD（~5%）が悪化しないか監視
3. ブラックリスト戦略除外後の新勝率推移を確認

### 最優先 — ACP Graduation Discord問い合わせ
4. 下記テンプレートでDiscord投稿（API証拠付き）

Discord投稿テンプレート:
    Agent: NeoAutonomous
    Agent ID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
    Wallet: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
    Chain: Base (8453)
    ISSUE: Stats shows "Stats not yet tracked" despite having metrics
    EVIDENCE: curl https://api.acp.virtuals.io/agents/019d7b3f-c2d8-7a52-839c-9629f4abb5dc/metrics
    Results: jobs=26, successRate=100%, volume=$6.90, revenue=$2.40, wallets=2
    UI shows: "Stats not yet tracked", No Graduation Progress, No Graduate Agent button
    Question: Is this a known V2 UI issue? How to proceed with graduation?

### 重要 — ACP seller v2対応
5. seller_native.tsをv2 NeoAutonomous(0x840C...)対応に改修
6. v2 SDK（AcpAgent + PrivyAlchemyEvmProviderAdapter）ベースのseller runtime

### 重要 — bt常時HIGH問題
7. バックテストconfidenceが常にHIGHで+15固定 → 情報価値なし、要調査

### 中期
8. Phase F3: Kelly基準ポジションサイジング（勝率60%安定後）
9. パターンマイニング（sell_tracker蓄積後）
10. Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 移行条件進捗（D3準拠）

| 条件 | 現在 | 必要 | 判定 |
|---|---|---|---|
| Paper勝率 | **49.4%（FIFOロット）** | 60%以上 | ❌ 未達（改善施策適用済み） |
| 継続期間 | 2026/04/03〜（12日） | 3ヶ月継続 | ⏳ 最短 07/03 |
| 取引回数 | 107件 | 100件完了 | ✅ 達成 |
| 学習モード | **OFF** | OFF（100回後） | ✅ 達成 |

---

## 新規ファイル・変更ファイル

| ファイル | 変更内容 |
|---|---|
| `core/config.py` | LEARNING_MODE=False, STRATEGY_BLACKLIST追加 |
| `research/backtests/run_backtest.py` | run_all_strategiesにブラックリストフィルタ追加 |
| `agents/trinity_council.py` | sentiment/reflexionスコアリング無効化 |

---

## ACP構成（v2移行後）

### Graduation対象: NeoAutonomous
- Agent UUID: 019d7b3f-c2d8-7a52-839c-9629f4abb5dc
- ウォレット: 0x840cff9032a4ce29845e05aed510f0ca4ea16cab
- acpV2AgentId: 41437（V1時代のID）
- cluster/tag: なし（OPENCLAWフラグなし）
- Offerings: 6件
- Jobs: 26件COMPLETED (chain 8453, successRate 100%)
- Stats UI: 未表示（VP側バグ） — metrics APIにはデータあり
- PRO ラベル: あり

### seller runtime状況
- neo-acp-seller.service: 稼働中だが旧ウォレット(0x3c6a...)に接続
- v2 NeoAutonomous(0x840C...)用のseller: 未構築
