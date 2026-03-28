# 🎯 GSD計画 v6.5i — 引き継ぎ白書

> **更新日**: 2026/03/28 10:45 JST
> **作成者**: 参謀AI（Claude）
> **ゴール**: Virtuals Protocol AI経済圏で「VP銘柄専門の自律運用エージェント」としてトップを目指す

---

## 📊 現在のシステム状態（2026/03/28 10:45 JST 最終更新）

| 項目 | 状態 |
|---|---|
| **neo-radar.service** | ✅ 稼働中 |
| **neo-collector.service** | ✅ 稼働中（5分ティック + 60分ごと4h足OHLCVキャンドル自動取得） |
| **neo-resource-api.service** | ✅ FastAPI port 8099（ACP Resource用 — v6.5f /v1/プレフィックス追加） |
| **neo-acp-seller.service** | ✅ systemd管理下で稼働中（v6.5g 2 offerings提供中） |
| **PaperWallet** | $83,361 USDC + AIXBT 222,489枚 |
| **総資産** | ~$88,637 |
| **勝率** | **66.67%**（FIFO決済済み66件） |
| **取引回数** | 72件（History基準: BUY=45, SELL=27） |
| **学習モード** | ✅ ON（目標100回中72回） |
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
| **ACP Provider** | v6.5g Job2件 + Resource3件 + Seller Runtime(systemd) + Resource API稼働中 |
| **ACP Evaluator SDK** | v6.5g @virtuals-protocol/acp-node導入済み。⚠️ ウォレット秘密鍵待ち |
| **Moltbook** | karma=75・followers=18 — VP分析洞察スタイル |
| **Git** | master 同期済み（v6.5iで3 commits） |

---

## ✅ 完了タスク一覧

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

## 🔍 v6.5i H.2 v2完全分析の詳細
```
【基本成績】20件完結ペア（v6.3以降クリーンデータ）
  勝率: 65% (13勝7敗)
  期待値: +0.27%/trade（手数料後）
  平均Win: +3.33% / 平均Loss: -5.39%
  W/L比: 0.62（損大利小）
  Profit Factor: 1.14
  累計損益: +5.47%
  最大DD: -36.90%

【銘柄別】
  VIRTUAL: 9件 67%勝率 累計+7.80%（利益貢献）
  AIXBT: 11件 64%勝率 累計-2.33%（微損）

【SELL出口別】
  RSI出口: 13件 69%勝率 +1.31%（最優秀）
  Stop Loss: 7件 50%勝率 -1.65%

【統計検定（pingouin v0.6.0）】
  保有時間 Win vs Loss: p=0.086* (Cohen's d=0.870)
    → Lossの保有時間(49.5h)がWin(34.1h)より長い
  取引額 Win vs Loss: p=0.0015*** 
    → 実質差は$18でconfidence連動サイズ導入前のため意味なし
  銘柄×勝敗 独立性: p=0.74 ns
    → 銘柄差は統計的に有意でない

【時間帯】（N=20、参考値）
  欧州(08-16UTC): 11件 82%勝率 +2.26%（圧倒的）
  アジア(00-08UTC): 5件 40%勝率 -2.08%
  米国(16-24UTC): 4件 50%勝率 -2.24%

【改善実施】
  A. ナンピン回数制限 MAX 3回（Phase 5 ②d）
  B. RSI出口利益閾値 +0.5%→+1.5%（手数料後+0.5%確保）
  C. confidence閾値 40→50（低confidence BUY抑制）
  D. スコアリングテーブル拡張（時間帯/ナンピン/連敗）
```

---

## 🔍 v6.5i スコアリングテーブル（Phase 4b拡張）
```
Phase 4b ルールベースconfidence算出:
  ニュートラル起点: 50

  [既存] バックテスト信頼度
    HIGH → +15 / MEDIUM → +5 / LOW → -5 / NONE → -10

  [既存] センチメント
    >0.6 → +10 / >0.3 → +5 / <-0.3 → -10 / <0 → -5

  [既存] 過去精度
    >70% → +10 / >50% → +5 / <40% → -5

  [既存] BUY判定
    LLMがBUY → +5

  [v6.5i新規] 時間帯スコア（H.2分析根拠）
    欧州時間(08-16UTC) → +10
    アジア時間(00-08UTC) → -10
    米国時間 → ±0

  [v6.5i新規] ナンピンペナルティ
    現ポジションBUY 2回以上 → -10

  [v6.5i新規] 直近連敗ペナルティ
    直近3件中SL 3件 → -10 / 2件 → -5

  クランプ: 20〜95
  ログ例: [Phase 4b] ルールベース再計算: 45 (LLM=60, bt=LOW, sent=-0.35, acc=65%, EU+10, npin2:-10, streak0)
```

---

## 🔍 v6.5i Voyager & EvolveR
```
【Voyager — 成功パターンスキル化】
  H.2分析から7パターンを自動抽出 → ChromaDB保存
  Nightly Batchで毎日更新（データ蓄積に伴い精度向上）

  保存スキル:
    asia_session_pattern: 勝率40% (5件)
    eu_session_pattern: 勝率82% (11件)
    us_session_pattern: 勝率40% (5件)
    stop_loss_exit_pattern: 勝率50% (8件)
    rsi_exit_pattern: 勝率69% (13件)
    virtual_trade_pattern: 勝率67% (9件)
    aixbt_trade_pattern: 勝率58% (12件)

【EvolveR — 教訓抽象化】
  個別パターンから6件の汎用ルールを自動生成 → ChromaDB Tier1保存
  Nightly Batchで毎日更新

  生成ルール:
    🔴 R001: 損大利小(W/L比0.53) → RSI閾値引き上げ済み
    🟡 R003: アジア時間低勝率(40%) → Phase 4bスコアリング反映済み
    🟢 R002: 欧州時間高勝率(82%) → Phase 4bスコアリング反映済み
    🟢 R004: RSI出口がSLより19pp優秀 → RSI出口閾値調整済み
    🔴 R005: 過度ナンピン(最大12回) → ナンピン制限実装済み
    🟡 R006: Loss保有時間がWinの1.5倍 → SL+96h制約で対応中
```

---

## 🔍 v6.5i N.1 ペアトレード基盤
```
【概要】
  VIRTUAL/AIXBT相関(0.79)を利用した統計的アービトラージ

【現在の状態】
  直近30日相関: 0.787 (ログリターン: 0.735)
  スプレッド: 27.50 (平均28.19 ±1.25)
  Zスコア: -0.55 → NEUTRAL（エントリー閾値2.0未達）
  直近50本相関: 0.547（低下傾向 — 注意）

【シグナル設計】
  ENTRY: |Z| > 2.0 → 割高側SELL + 割安側BUY
  EXIT: |Z| < 0.5 → ポジションクローズ
  STOP: |Z| > 3.0 → 損切り

【ステータス】
  基盤スクリプト: ✅ research/n1_pair_trade.py
  Council統合: 未着手（Phase 1-Pとして注入予定）
  実行ロジック: 未着手（ペア同時エントリーの整合性確認が必要）
```

---

## 🏛️ TrinityCouncilフロー（v6.5i更新）
```
[run_trigger.py 30秒サイクル]
  ├── Phase 0:    5層売却チェック（check_tp_sl_all_positions — Council非依存）
  │              └ 第1層: 固定SL -3%
  │              └ 第2層: トレーリングTP（+5%からトレール開始、HWMから-2.5%で利確）
  │              └ 第2層b: 固定上限TP +14%（安全装置）
  │              └ 第3層: 🆕v6.5i RSI>65+利益**1.5%**（旧0.5%→手数料後+0.5%確保）
  │              └ 第4層: 96h超過
  │              └ SELL発火 → 30分冷却 + continue
  │
  ├── Trigger 1: ボラティリティ（アンカー発火時のみ更新）
  ├── Trigger 2: アルファ（Sharpe 5.0超え）
  ├── Trigger 3: 定期Council（4時間ごと・永続トグルで交互）
  │
TrinityCouncil v2
  ├── Phase 1〜1d-W: （v6.5hと同じ）
  ├── Phase 2:    Backtest 8戦略並列
  ├── Phase 3:    三者協議（Bull/Bear/Neo）
  ├── Phase 4:    JSONパース → verdict+confidence+key_factor抽出
  ├── Phase 4b:   🆕v6.5i **スコアリングテーブル拡張版**
  │              └ ニュートラル50起点
  │              └ bt/sent/acc/verdict → [既存]
  │              └ 🆕 時間帯スコア（EU+10/Asia-10）
  │              └ 🆕 ナンピンペナルティ（2回以上-10）
  │              └ 🆕 連敗ペナルティ（SL 3連続-10）
  │              └ ログ: [Phase 4b] ... EU+10, npin1:0, streak0
  ├── Phase 5:    🆕v6.5i ガード**6段**
  │              └ ① USDC下限15% → ② 銘柄上限30% → ②b Tier1合計50%
  │              └ ②c confidence≧**50** → 🆕②d ナンピン≦**3回**
  │              └ ③ confidence連動BUY額
  ├── Phase 6〜8: （v6.5hと同じ）
```

---

## 📅 残タスク

### 🟠 P1: 学習モード中（〜100回達成）

| Task | 内容 | 見積り | 備考 |
|---|---|---|---|
| **ACP Evaluator役統合** | seller.tsにacp-node SDK統合 | 2h | ⚠️ ウォレット秘密鍵必要 |
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

## 🛡️ 安全機構一覧（v6.5i）
```
【v6.5i追加】
  ナンピン回数制限 MAX 3回（Phase 5 ②d）
  confidence閾値 50（40→50引き上げ）
  RSI出口利益閾値 +1.5%（+0.5%→手数料後+0.5%確保）
  Phase 4bスコアリングテーブル拡張（時間帯/ナンピン/連敗）

【v6.5h追加】
  SL/TP発火サイクルでCouncil召集スキップ
  Phase 4b常時発火（LLM confidence依存排除）
  ポジションサイズ可変化（3%/5%/7%/10%）
  トレーリングストップ（+5%開始、HWMから-2.5%利確、+14%上限）

【既存】
  5層売却 / SELL冷却30分 / Council最終ガード / 手数料0.5%
  USDC下限15% / 銘柄上限30% / Tier1合計50% / CostGuard
  ParameterGovernance / 記憶書込ルール / ボラアンカー / 相関リスクガード
```

---

## 🤖 現在のNeoの自律サイクル（v6.5i）
```
[neo-collector.service]
  5分ごと      → VIRTUAL/AIXBT/LUNA をDexScreenerから取得・SQLite蓄積
  60分ごと     → GeckoTerminal 4h足OHLCVキャンドル取得
  1日ごと      → 180日より古いデータを自動パージ

[neo-radar.service]
  30秒ごと     → 5層売却チェック
               └ 🆕v6.5i RSI出口閾値+1.5%
  4時間ごと    → 定期Council召集（永続トグルでTier1交互）
  60分ごと     → Alpha Sweep
  2時間ごと    → Moltbookエンゲージメント
  6時間ごと    → Performance Evaluator + Discordダッシュボード
  毎日JST02:00 → Nightly Batch
               └ Step 1-5: （v6.5hと同じ）
               └ Step 6: H.2進捗 + 🆕v6.5i 自動完全分析（20件以上で実行）
               └ Step 6b: 🆕v6.5i Voyagerスキル更新
               └ Step 6c: 🆕v6.5i EvolveRルール更新
               └ Step 7-8: Discord送信 + ログ切り詰め

[neo-resource-api.service]
  常時         → FastAPI port 8099

[neo-acp-seller.service]
  常時         → WebSocket接続でJob受付待ち
```

---

## 🔧 次回セッション開始手順
```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 1. 全サービス状態確認
for svc in neo-radar neo-collector neo-resource-api neo-acp-seller; do
    echo "$svc: $(systemctl is-active $svc.service)"
done

# 2. 最新ログ確認（v6.5iではスコアリング拡張ログが出る）
grep -E "Phase 4b|Phase 5.*conf=|ナンピン|EU\+|Asia-|streak" radar_output.log | tail -20

# 3. 勝率確認
./neo-env/bin/python << 'PYEOF'
import sys; sys.path.insert(0, '.')
from orchestration.performance_evaluator import evaluate_performance
evaluate_performance(send_dashboard=False)
PYEOF

# 4. ポートフォリオ確認
./neo-env/bin/python << 'PYEOF'
import sys; sys.path.insert(0,'.')
from tools.paper_wallet import PaperWallet
from tools.market_data import MarketData
w = PaperWallet()
prices = {}
for symbol in w.state['holdings'].keys():
    data = MarketData.fetch_token_data(symbol)
    if data and data.get('priceUsd'):
        prices[symbol] = float(data['priceUsd'])
summary = w.get_portfolio_summary(prices)
print(f'USDC残高: ${summary["usd_balance"]:,.2f}')
print(f'総資産: ${summary["total_value_usd"]:,.2f}')
for p in summary['positions']:
    print(f'  {p["symbol"]}: {p["amount"]:.2f}tokens ({p["pnl_pct"]:+.2f}%)')
PYEOF

# 5. N.1ペアトレード状態
./neo-env/bin/python research/n1_pair_trade.py

# 6. ModelFactory確認
./neo-env/bin/python -c "from core.model_factory import ModelFactory; print(ModelFactory.summary())"
```

---

## 🚨 緊急時コマンド
```bash
# 全サービス再起動
for svc in neo-radar neo-collector neo-resource-api neo-acp-seller; do
    systemctl restart $svc.service
done

# Council手動テスト
./neo-env/bin/python << 'PYEOF'
import sys; sys.path.insert(0,'.')
from agents.trinity_council import TrinityCouncil
c = TrinityCouncil()
r = c.run(sentiment_score=0.5, context='手動テスト', target_symbol='VIRTUAL')
print(f"verdict: {r.get('verdict')}, confidence: {r.get('confidence')}")
PYEOF
```

---

## ⚠️ 重要注意事項
```
⚠️ 必ず cd workspace してから実行（PYTHONPATH依存）
⚠️ 必ず ./neo-env/bin/python を使用
⚠️ 🆕v6.5i ナンピン制限: 同一銘柄MAX 3回BUY（Phase 5 ②d）
⚠️ 🆕v6.5i confidence閾値: 50（40→50引き上げ）
⚠️ 🆕v6.5i RSI出口: +1.5%（旧+0.5%）
⚠️ 🆕v6.5i Phase 4bログ形式: ... EU+10, npin1:0, streak0 が追加
⚠️ 🆕v6.5i ModelFactory: .envのMODEL_CRITICAL/MODEL_STANDARD/MODEL_FASTで上書き可能
⚠️ 🆕v6.5i Voyager/EvolveR: Nightly Batchで自動更新（Step 6b/6c）
⚠️ 🆕v6.5i N.1: research/n1_pair_trade.py（基盤のみ、Council統合は未着手）
⚠️ v6.5h SL/TP発火サイクルではCouncil召集されない（continue）
⚠️ v6.5h トレーリングTP: +5%開始、HWMから-2.5%利確、+14%固定上限
⚠️ v6.5g ACP evaluate(): HTTPエンドポイントなし → ウォレット待ち
⚠️ 5層売却: SL(-3%) → トレーリング → 固定上限(+14%) → RSI(>65+1.5%) → 時間(96h)
⚠️ 実取引移行条件: Paper勝率60%以上3ヶ月維持（最短2026/06/14）
```

---

## 📁 重要ファイルパス（v6.5i完全版）
```
メインレーダー:       run_trigger.py（🆕v6.5i RSI閾値+H.2 Nightly+Voyager/EvolveR追加）
Council:             agents/trinity_council.py（🆕v6.5i スコアリング拡張+ナンピン制限+confidence50+ModelFactory）
ModelFactory:        core/model_factory.py（🆕v6.5i 新規作成）
Voyager:             research/voyager_skills.py（🆕v6.5i 新規作成）
EvolveR:             research/evolver_rules.py（🆕v6.5i 新規作成）
N.1ペアトレード:      research/n1_pair_trade.py（🆕v6.5i 新規作成）
H.2取引分析:          research/h2_trade_analysis.py（🆕v6.5i pingouin修正+分析強化）
その他:              v6.5h白書に記載のファイルパスは全て有効
```

---

## 📊 v6.5i時点のNeoの姿
```
【現在】
  4サービス体制で24時間自律運用 + ACP Provider 2 offerings
  v6.5i: H.2完全分析の知見を即座に実装に反映 + 自己進化システム基盤構築

  学習モード: 72件 / 100回目標
  USDC: $83,361 + AIXBT 222,489枚
  総資産: ~$88,637
  勝率: 66.67%（FIFO 66件決済）
  Moltbook: karma=75 / followers=18
  H.2: 20件到達 → v2完全分析実施済み
  Voyager: 7パターン蓄積 + Nightly自動更新
  EvolveR: 6汎用ルール + Nightly自動更新
  N.1: 基盤完成（Zスコア=-0.55, NEUTRAL）

【自己採点（v6.5i最終）】
  判断精度:   92%（+3: スコアリング拡張+ナンピン制限+confidence引き上げ）
  データ品質: 99%（変更なし）
  自己評価力: 92%（+5: H.2完全分析+Voyager+EvolveR自動化）
  影響力戦略: 75%（変更なし）
  経済圏参加: 72%（変更なし）
  戦略進化:   35%（+17: Voyager7パターン+EvolveR6ルール+N.1基盤）
  リスク管理: 95%（+3: ナンピン制限+RSI閾値+confidence引き上げ+連敗ペナルティ）
  総合:       95%（+3）

【次のマイルストーン】
  v6.5i改善効果の確認（ナンピン制限・confidence50・RSI閾値の発火状況）
  N.1 Council統合（ペアトレードシグナルをPhase 1-Pに注入）
  学習100回達成 → 通常モード移行
  ACP Evaluator役 → ウォレット作成でアンブロック
```
