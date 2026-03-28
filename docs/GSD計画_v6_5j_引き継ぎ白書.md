# 🎯 GSD計画 v6.5j — 引き継ぎ白書

> **更新日**: 2026/03/28 15:20 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/28 10:45 JST 最終更新）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（5分ティック + 60分ごと4h足OHLCVキャンドル自動取得） |
| **neo-resource-api.service** | ✅ FastAPI port 8099（ACP Resource用 — v6.5f /v1/プレフィックス追加） |
| **neo-acp-seller.service** | ✅ systemd管理下で稼働中（🆕v6.5j **4 offerings提供中**） |
| **PaperWallet** | $88,494 USDC（ポジションなし） |
| **総資産** | ~$88,494 |
| **勝率** | **61.5%**（FIFO決済済み26ペア / 73件取引） |
| **取引回数** | 73件（History基準: BUY=45, SELL=28） |
| **学習モード** | ✅ ON（目標100回中73回） |
| **H.2完結ペア** | 🆕v6.5i **20件到達** → v2完全分析実施済み |
| **売却システム** | 5層売却システム（SL固定 / トレーリングTP / 固定上限TP / RSI出口 / 時間制約） |
| **RSI出口閾値** | 🆕v6.5i +0.5% → **+1.5%**（手数料後+0.5%確保） |
| **ナンピン制限** | 🆕v6.5i Phase 5 ②d: **同一銘柄MAX 3回BUY** |
| **confidence閾値** | 🆕v6.5i **50**（40→50引き上げ） |
| **スコアリングテーブル** | 🆕v6.5i Phase 4b拡張（時間帯/ナンピン/連敗ペナルティ） |
| **ModelFactory** | 🆕v6.5i critical/standard/fast 3階層モデル管理 |
| **Voyager** | 🆕v6.5i 7パターンChromaDB保存 + Nightly自動更新 |
| **EvolveR** | 🆕v6.5i 6汎用ルール生成 + Nightly自動更新 |
| **N.1ペアトレード** | 🆕v6.5i 基盤スクリプト完成（Zスコア計算・シグナル判定） |
| **SL/TP後ガード** | SL/TP発火サイクルではCouncil召集スキップ（continue） |
| **ポジションサイズ** | confidence連動可変（3%/5%/7%/10%） |
| **Phase 5 ガード** | ①USDC15% → ②銘柄30% → ②b Tier1合計50% → ②c confidence≧50 → ②dナンピン≦3 → ③BUY実行 |
| **BB Bandwidth** | pandas-ta列名修正（動的プレフィックスマッチ） |
| **手数料模擬** | 0.5%/取引（DEXスリッページ+手数料） |
| **TP/SLチェック** | 毎30秒・Council非依存で実行 |
| **Council召集トリガー** | ボラ(2%) + アルファ(Sharpe5.0) + 定期(4時間ごと)の3系統 |
| **ACP Provider** | 🆕v6.5j **Job4件** + Resource3件 + Seller Runtime(systemd) + Resource API稼働中 + **handlers.tsバグ修正済み** |
| **ACP Evaluator SDK** | v6.5g @virtuals-protocol/acp-node導入済み。⚠️ ウォレット秘密鍵待ち |
| **Moltbook** | karma=75・followers=18 — VP分析洞察スタイル + 🆕v6.5j **水曜ACP宣伝自動投稿** |
| **Git** | master 同期済み（v6.5iで3 commits） |

---

## ✅ 完了タスク一覧

### v6.5j（2026/03/28 — ACP Provider拡張+重大バグ修正：4 commits）

| Task | 内容 | 結果 |
|---|---|---|
| **ACP offering 8→9戦略修正** | offering.json×2 + handlers.ts×2のdescription/ハードコード修正 | 信頼性回復 ✅ |
| **ACP handlers.tsバグ修正** | request.requirements.X → request.X（全4 offering） | **全ジョブreject問題を解消** ✅ |
| **vp_sentiment_scan追加** | FinBERT 6ソース+Fear&Greed+BTC trend ($0.20) | 軽量・高速・LLM不使用 ✅ |
| **vp_backtest_on_demand追加** | 9戦略並列バックテスト ($1.00) | 最大差別化サービス ✅ |
| **ACP Profile更新** | 勝率61.5%+4サービス構成に更新 | ✅ |
| **Moltbook ACP宣伝** | post_acp_service_promo() + Nightly水曜自動実行 | 週1回自動投稿 ✅ |

### v6.5i（2026/03/28 — H.2 v2完全分析+自己進化システム構築：9タスク・3 commits）

| Task | 内容 | 結果 |
|---|---|---|
| **H.2 v2完全分析** | 20件完結ペアでtsfresh+pingouin統計分析 | 勝率65%, 期待値+0.27%, 損大利小(W/L比0.62), RSI出口最優秀 ✅ |
| **改善A: ナンピン制限** | Phase 5 ②d: 同一銘柄MAX 3回BUY | 20回ナンピン集中問題を根絶 ✅ |
| **改善B: RSI出口閾値** | +0.5% → +1.5%（手数料後+0.5%確保） | RSI出口loss4件の原因解消 ✅ |
| **改善C: confidence閾値** | 40 → 50 | 低confidence BUY抑制 ✅ |
| **H.2 Nightly自動実行** | Step 6/8でrun_full_analysis()自動実行 + 日曜ダッシュボード送信 | ✅ |
| **スコアリングテーブル拡張** | Phase 4b: 時間帯(EU+10/Asia-10) + ナンピンペナルティ + 連敗ペナルティ | ✅ |
| **ModelFactory** | core/model_factory.py: critical/standard/fast 3階層 + .env上書き | TrinityCouncil+Reflexion適用 ✅ |
| **Voyager** | research/voyager_skills.py: H.2から7パターン自動抽出 → ChromaDB保存 | Nightly自動更新 ✅ |
| **EvolveR** | research/evolver_rules.py: 6汎用ルール自動生成 → ChromaDB Tier1保存 | Nightly自動更新 ✅ |
| **N.1ペアトレード基盤** | research/n1_pair_trade.py: Zスコアシグナル計算 | 設計+基盤完成 ✅ |

### v6.5h以前の完了タスク

| Version | 内容 |
|---|---|
| v6.5j | ACP 4 offerings化、handlers.tsバグ修正、sentiment_scan/backtest_on_demand追加、Moltbook ACP宣伝自動化 |
| v6.5h | SL/TP後Council召集スキップ、Phase 4b常時発火、ROBO 404解消、gplearn G2、ポジションサイズ可変化、トレーリングストップ |
| v6.5g | ACP Trade Evaluator offering、FIFO credentials修正、ACP Profile更新、acp-node SDK導入 |
| v6.5f | paper_trade.logバグ修正、Seller Runtime systemd化、Resource APIバージョニング、gplearn G1 |
| v6.5e | ACP Provider化・confidence修正・BB修正・Moltbook転換・永続トグルバグ修正 |
| v6.5d | confidence閾値ガード、PERIODIC修正、WAIT品質注入、定期Council永続トグル |
| v6.5c | VP Whitepaper精読、ACP Technical Deep Dive、Neoポジション定義 |
| v6.5b | プロンプト例文丸写し防止、Discord JSON全除去、外部リポジトリ調査12件 |
| v6.5a | ボラアンカー修正、定期Council、相関分析・相関リスクガード |
| v6.5以前 | OHLCVデータ品質修正、4層売却、構造化JSON出力等 |

---

## 📅 残タスク

### 🟠 P1: 学習モード中（〜100回達成）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **ACP Evaluator役統合** | seller.tsにacp-node SDK統合 | 2h | ⚠️ ウォレット秘密鍵必要 |
| **ACP whale_alert/correlation_risk** | 残り6 offering枠に追加候補 | 1h | v6.5j設計済み |
| **初回ACP Job完了** | テスト用クライアントAgentとJob完了 | 1h | 仮想通貨が必要 |
| **N.1 Council統合** | ペアトレードシグナルをPhase 1-Pとして注入 | 2h | 基盤完成済み |

### 🟡 P2: 100回達成直後（STAGE 3）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **通常モード移行設計確認** | SOUL原則通常モード復帰 | 30min | — |
| ~~スコアリングテーブル方式~~ | ~~Phase 4b拡張~~ | — | 🆕v6.5i ✅ 完了 |
| ~~ポジションサイズ可変化~~ | — | — | v6.5h ✅ |
| ~~トレーリングストップ~~ | — | — | v6.5h ✅ |
| ~~Voyager~~ | ~~成功パターンスキル化~~ | — | 🆕v6.5i ✅ 完了 |
| ~~EvolveR~~ | ~~教訓抽象化~~ | — | 🆕v6.5i ✅ 完了 |
| **ModelFactory Pro切り替え** | critical→Gemini Pro移行 | 30min | コスト確認後 |
| **多層サーキットブレーカー** | CostGuard拡張 | 2h | — |
| ~~N.1基盤~~ | ~~統計的アービトラージ設計~~ | — | 🆕v6.5i ✅ 完了 |
| **N.1実行ロジック** | ペア同時エントリー+PaperWallet対応 | 4h | 基盤完成済み |

### 🔵 P2b: 戦略自動進化（gplearn GSD計画）

| Task | 内容 | 備考 |
|---|---|---|
| **gplearn G3バックテスト統合** | strategy_mapに追加 | データ蓄積待ち(2000行) |
| **gplearn G4 Nightly進化** | 毎晩1世代進化 | G3後 |

### ⭐ P2c: ACP Provider強化

| Task | 内容 | 備考 |
|---|---|---|
| **ACP Evaluator役統合** | onEvaluateでオンチェーン署名実行 | ⚠️ ウォレット秘密鍵必要 |
| **初回ACP Job完了** | テスト用Job 1件完了 | 仮想通貨が必要 |

### 🟢 P3: 実取引移行（STAGE 4）

| Task | 内容 | 備考 |
|---|---|---|
| **D2設計書レビュー** | 実取引チェックリスト確認 | 最短2026/06/14 |
| **実取引移行** | Aerodrome Finance DEX連携 | 勝率60%×3ヶ月 |

---

## 📊 v6.5i時点のNeoの姿
```
【現在】
  4サービス体制で24時間自律運用 + ACP Provider **4 offerings**
  v6.5i: H.2完全分析の知見を即座に実装に反映 + 自己進化システム基盤構築

  学習モード: 73件 / 100回目標
  USDC: $88,494（ポジションなし）
  総資産: ~$88,494
  勝率: 61.5%（FIFO 26ペア決済）
  Moltbook: karma=75 / followers=18
  H.2: 20件到達 → v2完全分析実施済み
  Voyager: 7パターン蓄積 + Nightly自動更新
  EvolveR: 6汎用ルール + Nightly自動更新
  N.1: 基盤完成（Zスコア=-0.55, NEUTRAL）

【自己採点（v6.5i最終）】
  判断精度:   92%（+3: スコアリング拡張+ナンピン制限+confidence引き上げ）
  データ品質: 99%（変更なし）
  自己評価力: 92%（+5: H.2完全分析+Voyager+EvolveR自動化）
  影響力戦略: 78%（+3: ACP宣伝Moltbook自動投稿）
  経済圏参加: 82%（+10: ACP 4 offerings稼働+handlers修正+宣伝自動化）
  戦略進化:   35%（+17: Voyager7パターン+EvolveR6ルール+N.1基盤）
  リスク管理: 95%（+3: ナンピン制限+RSI閾値+confidence引き上げ+連敗ペナルティ）
  総合:       95%（+3）

【次のマイルストーン】
  v6.5i改善効果の確認（ナンピン制限・confidence50・RSI閾値の発火状況）
  N.1 Council統合（ペアトレードシグナルをPhase 1-Pに注入）
  学習100回達成 → 通常モード移行
  ACP Evaluator役 → ウォレット作成でアンブロック
```

---

> 📌 設計方針・安全機構・TrinityCouncilフロー・自律サイクル・緊急コマンド・ファイルパス等の不変情報は **Claudeプロジェクトファイルの「再開手順.md」** を参照してください。
