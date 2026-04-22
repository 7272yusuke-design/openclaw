# GSD計画 v6.5be 引き継ぎ白書

- 更新日時: 2026/04/22 JST
- セッション: v6.5be（Phase 4c — ルールベースverdict決定権の確立 + V7方針確定）
- 自己採点: 8/10（主要改修完了、方針明確化、観察体制整備）

---

## 🎯 本セッションの主要成果

### 🥇 Phase 4c新設 — 取引停止の真の根本原因を解消
- **問題**: Phase 4bはconfidenceのみ上書きし、verdictはLLMが独占
  - 直近10回Council全WAIT、スコア78点出ても無視
  - strat+5(atr_breakout:66.7%)の「戦略がはまった瞬間」も黙殺
- **解決**:
  1. Phase 4c新設: calc_conf >= 65でBUY、<45でWAIT、45-64はLLM判定を尊重
  2. RISK_ON_RIDE加点: 0 → +3
  3. bt=HIGH連動戦略フィットボーナス(+3〜+5)

### 🥈 次世代エージェント設計方針の確定
ユーザー構想「どんな相場でも戦略がはまった瞬間に取引 / 戦略と変化への柔軟性 / LLMは戦略選定」を
次世代設計観点で評価:
- 構想は7割正しい
- 不足要素: 戦略ポートフォリオ化、メタ戦略学習(L3)、edge/confidence/sizing分離

### 🥉 Level 3ベース機能の現状診断
- **gplearn**: 生成OKだが精度43%で意図的blacklist
- **Voyager**: VoyagerSkillsクラス欠損、実態不明
- **EvolveR**: ルール生成OKだがscoring_adjustments.json空(転記パイプ断絶)
- **Alpha Sweep**: 発見OKだがBlackboard未書込
- **結論**: 「Level 3実装済み」は誤認。部品散在状態

### 🏅 戦略B採択 — D3優先、V7は後回し
理由: Phase 4cで取引を回す→データ蓄積→そのデータでLevel 3部品修復、が最合理

---

## 🔴 現状数値

- 勝率(FIFO): 75.8% (33ペア決済)
- USDC: $79,258.82
- Holdings: BTC(0.1177)
- Evaluator勝率: 51.76% (85件)

---

## ⏭️ 次セッションの作業(優先順)

### 観察フェーズ(今日〜1週間)
観察スクリプト `bash tools/v65be_observation.sh` を毎日1回実行

### 判断トリガー(発生時のみClaudeセッション再開)
1. 24時間Phase 4c未発火
2. BUY発火するがPhase 5全弾かれ
3. 3連続SL発火
4. Evaluator勝率45%以下に下落
5. エラーで取引停止

### V7-α着手判断(+1ヶ月後)
D3進捗(勝率・取引回数)を見て、V7-α(既存部品修復)の必要性を判断

---

## 📋 V7ロードマップ(戦略B)

- 現在 〜 2026/06 : Phase 4c観察、D3移行準備
- 2026/06 〜 /08  : D3 Binance本番移行、実資金で取引
- 2026/08 〜 /10  : V7-α(EvolveR転記、Voyager整理、Alpha Sweep接続、gplearn決着)
- 2026/10 〜 /12  : V7-β(LLM役割をLevel 1〜2へ、戦略選定者化)
- 2027/01 〜      : V7-γ(真のLevel 3、戦略DSL、戦略ポートフォリオ、Kelly sizing)

---

## 📁 本セッションで作成・変更したもの

- 編集: agents/trinity_council.py (Phase 4c追加、RISK_ON_RIDE 0→+3、bt=HIGH連動fit bonus)
- 新規: tools/v65be_observation.sh (観察ダッシュボードスクリプト)
- バックアップ: .archive_deadcode_v65p/trinity_council.py.bak_v6.5be_verdict_override (ロールバック用)
- 新規: docs/GSD計画_v6.5be_引き継ぎ白書.md (本ファイル)

---

## 🔐 ロールバック手順
cd /docker/openclaw-taan/data/.openclaw/workspace && cp .archive_deadcode_v65p/trinity_council.py.bak_v6.5be_verdict_override agents/trinity_council.py && systemctl restart neo-radar.service
---

## 📌 重要な認識修正事項

### 白書の虚構を修正
- ARCHITECTURE.mdの「Voyager(パターン学習)」→ クラス欠損、実態不明
- 白書の「Voyager 6〜8件で安定」→ 確認できず
- Level 3「ベース機能実装済み」の表現 → 「部品散在状態」が正確

### 正しい現状
- 「発見/学習」レイヤーは部分稼働
- 「記録」レイヤーで断絶
- 「取引判定への接続」レイヤー未実装
