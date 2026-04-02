# 📐 GSD計画 v6.5ac 引き継ぎ白書

> **更新日時**: 2026/04/02 22:30 JST
> **セッション**: v6.5ac（Market Intelligence offering + 自己進化E1実装セッション）
> **自己採点**: 90/100（MI offering完成・E1実装完了・E4.1モデル確認・ロードマップ策定）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続（AIXBT 50%が主因） |
| Tier0勝率 | 0%（BTC/ETH取引開始待ち — 初回BTC Council完了→WAIT判断） |
| USDC | $87,979.91 |
| Holdings | なし |
| サービス | 全4サービス稼働中 + **vp_market_intelligence NEW** |
| CFO L4 | ドローダウンブロック発動中（HWM $88,494） |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄・AIXBTはTier2降格） |
| 自己進化 | **E1実装完了** — 構造化内省+entry_context保存+failure_category |
| モデル | MODEL_FAST=gemini-2.5-flash（.env設定済み） |

---

## ✅ 本セッション完了タスク

### Task 1: Market Intelligence offering（柱1）
- **Council analysis_onlyモード追加**: `TrinityCouncil.run(analysis_only=True)`
  - Phase 1〜4b（情報収集・三者協議・スコアリング）実行
  - Phase 5〜8（取引・Discord・Moltbook・メモリ）スキップ
  - 12フィールドのリッチレポート辞書をreturn
- **vp_market_intelligence offering新規作成** ($0.50)
  - quickモード（~30秒）: テクニカル+センチメント+バックテスト→簡易シグナル
  - fullモード（~120秒）: Council三者協議+スコアリング内訳+Bull/Bear論争
  - 対応銘柄: VIRTUAL, AIXBT, BTC, ETH
  - Neo実績（勝率・決済数）自動添付
- **テスト完了**: analysis_only=TrueでWAIT判断が正常返却（取引ゼロ・Discord投稿ゼロ確認）

### Task 2: 自己進化ロードマップ策定
- 5つの構造的問題を診断（P1:内省浅い, P2:Reflexion浅い, P3:EvolveR手動, P4:失敗分類なし, P5:閉ループなし）
- 4フェーズ計画（E1〜E4）を設計・文書化
- `docs/neo_self_evolution_roadmap.md` + Claudeプロジェクトファイルに保存

### Task 3: E1 深い内省（Deep Introspection）— 実装完了
- **E1.1**: SL発火時の内省を100字自由文 → 7カテゴリ構造化JSONに置換
  - failure_category: trend_against / btc_correlation / overconfidence / bad_timing / signal_false / volatility_spike / averaging_down
  - エントリー時コンテキスト（RSI/sentiment/confidence/BTC）を内省プロンプトに注入
  - JSONパース失敗時は従来のフォールバック内省に戻る
- **E1.3**: BUY時にentry_contextをholdingsに保存（Phase 5 strategy_tag保存の直後）
  - rsi_14, sentiment_score/label, bt_confidence, confidence, scoring_breakdown, btc_24h/trend, key_factor, timestamp
- **E1.4**: ChromaDB trade_result metadataにfailure_category追加（E2/E3の入力ソース）

### Task 4: E4.1 モデル確認+設定
- gemini-2.5-flash / gemini-2.5-pro 両方利用可能を確認（google-generativeai v0.8.6）
- `.env`にMODEL_FAST=gemini-2.5-flash設定 → 内省品質向上
- MODEL_CRITICAL / MODEL_STANDARD は現状維持（gemini-2.0-flash）

### Task 5: ACP サービス戦略ブレスト
- 3本柱を策定: Market Intelligence（柱1） / Agent Rating（柱2） / Strategy Data Licensing（柱3）
- 柱1を最優先で「売り物レベル」に引き上げる方針決定
- 既存4 offeringの問題点特定: 全てデータダンプ止まり、Council判断が含まれていない

---

## ⏭️ 次セッションの作業

### 短期（次回）
1. **E1検証**: 次のSL発火で構造化内省JSONが正しく生成されるか確認（ログ監視）
2. **E2実装**: Reflexionプロンプト高度化 + confidence_adjustmentのPhase 4b注入 + 閉ループ検証
3. **2hローテーション観測**: BTC→VIRTUAL→ETH が正しく発火するか確認
4. **Graduation Discord返答確認**: NeoAutonomous Graduateボタン問題のDevRel回答待ち

### 中期
5. **E3実装**: EvolverAgent新規作成 + scoring_adjustments.json自動生成 + Phase 4b動的読み込み
6. **E4.3-4**: criticalモデルA/Bテスト（gemini-2.5-pro vs flash）
7. **ACP登録**: vp_market_intelligenceをNeoAutonomousのofferingとして登録（Graduation問題解決後）
8. **旧offering整理**: sentiment_scan / backtest_on_demand のACP登録解除検討
9. **Phase 4: 実取引エンジン（Binance Spot API）** — `tools/cex_executor.py` 新設

---

## 🔒 OpenClawアップデートメモ（Graduation後に対応）

| 項目 | 値 |
|---|---|
| 現在のバージョン | **2026.2.19**（ビルド日: 2026-02-20） |
| 最新安定版 | **2026.3.31**（6週間・13リリース分の遅れ） |
| 結論 | 緊急対応不要。Graduation完了後にアップデート推奨 |

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `agents/trinity_council.py` | analysis_onlyモード追加、entry_context保存（E1.3） |
| `run_trigger.py` | 構造化内省プロンプト（E1.1）、failure_category metadata追加（E1.4） |
| `offerings/vp_market_intelligence/` | **新規** — handlers.ts + offering.json |
| `.env` | MODEL_FAST=gemini-2.5-flash追加 |
| `docs/neo_self_evolution_roadmap.md` | **新規** — 自己進化ロードマップ |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | Nightly自動更新 |
| evolver_rule | 36件 | Nightly自動更新（スコアリング反映は手動→E3で自動化予定） |
| trade_result | 31件 | **E1実装により次回以降failure_category付きで保存** |

### E1〜E4 進捗

| Phase | 名称 | ステータス | 残作業 |
|---|---|---|---|
| E1 | 深い内省 | ✅ **実装完了** | SL発火での実地検証待ち |
| E2 | 進化するReflexion | 🔲 未着手 | Reflexionプロンプト+confidence_adjustment+閉ループ |
| E3 | 自律ルール適用 | 🔲 未着手 | EvolverAgent+scoring_adjustments.json+Phase 4b読み込み |
| E4 | モデル最適化 | 🟡 E4.1完了 | A/Bテスト（E1-E3完了後） |

---

## 📈 勝率分析サマリー

| 銘柄 | 決済ペア | 勝 | 負 | 勝率 | 備考 |
|---|---|---|---|---|---|
| VIRTUAL | 10 | 7 | 3 | **70.0%** | 健全 |
| AIXBT | 18 | 9 | 9 | **50.0%** | 3/26以降ほぼ全敗。Tier2降格で比率低下中 |
| BTC | 0 | — | — | — | 初回Council→WAIT |
| ETH | 0 | — | — | — | ローテーション追加済み |
| **合計** | **28** | **16** | **12** | **57.1%** | 60%割れ継続 |
