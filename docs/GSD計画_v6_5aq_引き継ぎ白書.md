# 📐 GSD計画 v6.5aq 引き継ぎ白書

> **更新日時**: 2026/04/06 12:00 JST
> **セッション**: v6.5aq（デバッグ検証・戦略実行改善・Moltbookデータ駆動化）
> **自己採点**: 82/100（戦略実行パイプライン構築完了。蓄積・効果検証待ち）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | リセット後 **1ペア**（蓄積中） |
| USDC | 確認要（DD4.9%付近） |
| Holdings | VIRTUAL / ETH / BTC（複数ポジション） |
| サービス | 全4サービス稼働中 |
| CFO L4 | DD4.9% — ギリギリALL CLEAR |
| Council | **1h**ローテーション: BTC → VIRTUAL → ETH（3銘柄） |
| bt_confidence | **HIGH** |
| 設計転換 | 入口ゲート→出口管理（BUY閾値30, conf連動サイズ） |
| 自己進化 | E1-E3+Phase1e+F5+Phase S(S1-S4)+F2b — 8層進化スタック |
| モデル | MODEL_FAST=gemini-2.5-flash |

---

## ✅ 本セッション完了タスク

### Task 1: v6.5ap デバッグ効果検証
- Phase 4bスコア: 34〜58（旧22-47から改善）✅
- Phase 5 BUY: 8件実行、ナンピン上限ガード正常 ✅
- conf連動サイズ: 42→3%, 52→3%, 57→5%, 58→5% ✅
- S2戦略モニタリング: VIRTUAL/ETH追跡動作中 ✅
- Scout Sharpe実計算: 修正後動作（21.87, 6.19, -27.08等）✅
- E2 Reflexion: adj=-5/-3, バイアス検出OK ✅
- K.3クジラ: 動作中（検出0件は市場静か）✅

### Task 2: Phase 3b RR≧1.5フィルタ追加
- **問題**: RR=0.22やRR=0.17の低品質戦略が素通りしていた
- **修正**: `_rr_ok = _rr_ratio >= 1.5`のハード制約追加
- 品質不足時のログに`RR=X.XX<1.5`を表示

### Task 3: ATR計算修正
- **問題**: `"df" in dir()`が常にFalse → ATR=0.0%固定
- **原因**: Council内にOHLCVデータ取得が一切なかった
- **修正**: `MarketData.fetch_ohlcv_custom(target_symbol, days=7)`を追加

### Task 4: CoinGecko 429時Binanceフォールバック
- **問題**: CoinGecko 429 → DexScreener → Base chain低流動性プールの歪み価格（ETH+43%乖離）
- **修正**: CoinGecko失敗 → 30分キャッシュ → **Binance** → DexScreenerの順に変更
- BTC/ETH/SOL/BNBに対応（APIキー不要のパブリックエンドポイント）

### Task 5: L4ドローダウンログスパム抑制
- **問題**: DD5.0%境界で30秒毎にBLOCKED/CLEARを交互出力
- **修正**: `_l4_blocked`フラグで状態変化時のみ出力

### Task 6: exit_stages構造化（戦略実行パイプライン）
- **問題**: LLMの戦略書(take_profit_plan)が自由テキストで機械実行不可能。全ポジション全量売却のみ
- **修正3段階**:
  1. LLMプロンプト: `take_profit_plan`(テキスト) → `exit_stages`(JSON配列)に変更
     - bull: `[{trigger_pct, sell_pct, note}, ...]` 最低2段階、最終=100%
     - bear: `[{trigger_pct(負数), sell_pct=100, note}]`
  2. バリデーション: LLMがexit_stages未出力時はtarget_pct/risk_pctからデフォルト生成
  3. Phase 0: exit_stagesに従い段階的売却。completed_stagesで発火済みstageをマーキング
- PaperWalletの部分売却機構（既存）を活用

### Task 7: Moltbookデータ駆動化
- **問題**: 全投稿が抽象的ポエム → karma増加ゼロ
- **修正**: Council分析データ(sentiment/RSI/CFP/confidence/BTC変動/best strategy)をMoltbookに渡す
- WAIT投稿: 具体的数値を含む市場観察（例: "RSI at 28, capital flow risk-off..."）
- BUY/SELL投稿: 判断根拠の数値共有（例: "Confidence 58/100, RSI oversold..."）
- フォールバックも数値入りテンプレート

---

## ⏭️ 次セッションの作業

### 最優先 — 本セッション修正の効果検証
1. `grep "ATR=" radar_output.log | tail -5` → ATR値が0以外か
2. `grep "RR=.*<1.5" radar_output.log | tail -5` → RRフィルタ動作確認
3. `grep "Binance fallback" radar_output.log | tail -5` → Binance使用確認
4. `grep "Exit Stage" radar_output.log | tail -5` → 段階的売却動作確認
5. `grep "MoltbookTool" radar_output.log | tail -5` → 投稿がデータ駆動か確認
6. Moltbook karma推移確認

### 重要 — DexScreener ETH価格乖離（追加対策）
- Binanceフォールバックで主要銘柄は解決
- VP銘柄(VIRTUAL)はGeckoTerminal優先で問題なし

### 検証待ち
7. S2/S3: BUY後の戦略書モニタリング・動的出口の動作確認
8. E1検証: SL発火でscenario_outcome+strategy_quality_score確認
9. 拡充メタデータ: 次回SELL/SL時にconf_total/tz/cfr等が正しくChromaDBに保存されるか確認
10. exit_stages: 部分売却後のcompleted_stages永続化確認

### 短期 — パターンマイニング実装
11. 50件蓄積後: `research/pattern_miner.py` 作成（Apriori + 異常検知）
12. 発見ルールを `vault/mined_patterns.json` に保存 → Phase 4bでスコア調整に活用

### その他
13. VP/Graduation: Discord返答確認
14. E3拡張: 戦略パターンルール自動生成（strategy_quality_score蓄積後）

### Phase F3: Kelly基準ポジションサイジング（勝率60%回復後）
### Phase F4: Markowitz配分最適化（BTC/ETH実績蓄積後）

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| agents/trinity_council.py | Phase 3b: RR≧1.5フィルタ追加、ATR用OHLCV取得追加、exit_stagesプロンプト・バリデーション追加、Phase 6: market_data渡し追加 |
| run_trigger.py | Phase 0: exit_stages判定+段階的売却実装、sell_amount_usd *= _sell_fraction |
| tools/market_data.py | CoinGecko 429時Binanceフォールバック追加（BTC/ETH/SOL/BNB） |
| tools/moltbook_tool.py | WAIT/BUY/SELL投稿をデータ駆動に全面書き換え、market_data引数追加 |
| core/cost_guard.py | L4ログ重複抑制（_l4_blockedフラグ） |

---

## 📢 Discord報告体系（変更なし）

| 報告 | タイミング | 内容 |
|---|---|---|
| Council Minutes | BUY/SELL時 | 市況+ポジション+戦略書+スコアリング内訳+判断+取引結果+出口プロファイル |
| Performance Dashboard | 6h毎 | 勝率+Tier別+ポートフォリオ（戦略進行度・PnL USD付き）+直近決済5件 |
| Nightly Batch Report | JST 02:00 | 自己進化日報: Voyager学習+EvolveR進化+gplearn G4+WAIT品質+直近教訓 |
| Moltbook活動レポート | JST 02:00 | karma推移+エンゲージメント+submolt別パフォーマンス |

---

## 🛡️ リスクヘッジ全レイヤー

| 検知対象 | 仕組み | 頻度 | 対応速度 |
|---|---|---|---|
| BTC急落 | F2（L1-L3） | 30秒 | 即時 |
| マクロ急変（SPY/Gold） | F2b（L1-L3） | 30分 | 先回り |
| マクロ環境悪化 | F5 capital_flow_phase | 1h | Council時 |
| **戦略書exit_stages** | **Phase 0第0層（新設）** | **30秒** | **即時** |
| ポジション個別 | Phase 0 5層出口 | 30秒 | 即時 |
| 戦略前提崩壊 | Phase S invalidation | 30秒 | 即時 |
| ポートフォリオ全体 | CostGuard L1-L4 | Council時 | 1h |
| ポートフォリオ集中 | Phase 5ガード6段 | BUY時 | 即時 |

---

## 🧬 自己進化システム状態

| コンポーネント | 件数 | ステータス |
|---|---|---|
| ChromaDB全体 | 377+件 | 正常 |
| trade_record | 152件 | 構造化済み |
| wait_record | 103件 | 構造化済み |
| voyager_skill | 42件 | **データ不足待機中**（クローズドペア10件必要、現在1件） |
| evolver_rule | 36件 | **データ不足待機中**（同上） |
| trade_result | 31件 | 18項目メタデータ拡充済み |
| reflexion_result | 4件 | E2動作中（adj=-5/-3確認） |
| macro_data | 5指標 | F5日次自動更新 |
| gplearn | 動作中 | VIRTUAL acc=34.69% / AIXBT acc=48.47% |
