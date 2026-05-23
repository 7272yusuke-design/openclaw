# 🔄 Neo 再開手順・永続リファレンス

> **最終更新**: 2026/04/04 v6.5ak

---

## 最初にやること

新しいセッションを開始したら、まず以下を実行して最新の引き継ぎ白書とアーキテクチャマップを読み込んでください。

```bash
cat "$(ls -t /docker/openclaw-taan/data/.openclaw/workspace/docs/GSD計画*.md | head -1)"
cat /docker/openclaw-taan/data/.openclaw/workspace/ARCHITECTURE.md
```

- **白書**: 現在のシステム状態・完了タスク・残タスク・自己採点（毎セッション変わる）
- **ARCHITECTURE.md**: ファイル構成・呼び出しフロー・ACP構成・データ所在（構造変更時のみ更新）
- **本ファイル（再開手順）**: 設計方針・安全機構・禁止事項・緊急コマンド（めったに変わらない）

---

## ドキュメント配置

| ドキュメント | 場所 | 内容 |
|---|---|---|
| **引き継ぎ白書** | サーバー `docs/GSD計画_v*_引き継ぎ白書.md`（最新版を自動検出） | 毎セッション変わるもの（状態・タスク） |
| **ARCHITECTURE.md** | サーバー `ARCHITECTURE.md` | ファイル構成・依存関係・呼び出しフロー・ACP構成（構造変更時のみ更新） |
| **再開手順**（本ファイル） | Claudeプロジェクトファイル | めったに変わらないもの（設計・ルール・フロー） |

---

## 環境ルール（必須）

- **作業ディレクトリ**: `/docker/openclaw-taan/data/.openclaw/workspace`
- **Python**: `./neo-env/bin/python`（system pythonは不可）
- **ACP CLI**: `skills/virtuals-protocol-acp/` から `npx tsx bin/acp.ts`
- **.env**はgitにコミットしない
- **バックアップファイル**（`.bak*`）は作成後すぐ `.archive_deadcode_v65p/` に移動する。ソースディレクトリに残さない（`.gitignore`で`.bak*`は除外済み）

---

## 設計方針（変えてはいけないもの）

- TrinityCouncilのBull/Bear/Neo三者構造は変えない
- ACP外部エージェントのシグナルは「参考情報注入のみ」（方針X）
- 銘柄監視: Tier0=BTC/ETH（ローテーション）、Tier1=VIRTUAL（常時）、Tier2=LUNA（60分）
- AIXBTは対象外（Tier2降格後、取引対象から除外）
- Discovery銘柄（ROBO/TIBBIR/GAME等）はCouncil召集せず監視・Discord報告のみ
- Alpha Sweep自動更新はBlackboardのみ書き込む（ChromaDBに書かない）
- LLMのconfidenceは参考値のみ → Phase 4bルールベースで常に上書き
- LLMは「戦略家」として活用（予測ではなくシナリオ設計）

---

## やってはいけないこと

- CostGuardをreturn Trueで無効化する
- Discovery銘柄でCouncil召集する（バックテストデータ不足で常にWAITになる）
- Moltbookに取引推奨投稿（BUY/SELL/$金額）をする（スパム判定される）
- system pythonでパッケージをインストールする
- Phase 3bの戦略書でrisk_pct > 6%のSL設定を許可する

---

## 過去の重大バグ（再発防止）

- `fetch_ohlcv_custom`が合成データを返していた → Sharpe常時5.0超え → 修正済み
- TrinityCouncilがBUY後にテキスト生成のみで取引未実行 → 修正済み
- ChromaDBがAlpha Sweepノイズで汚染（59件→17件）→ 書き込みルール制定済み
- Blackboardに旧銘柄データが残存してAVAX等がCouncil召集された → クリーンアップ済み
- ACP handlers.tsが`request.requirements.X`で参照 → 全ジョブreject → v6.5j修正済み
- streak連敗ペナルティが48h経過後も残存 → 取引2日間停止 → v6.5rで48h完全解除に修正
- L4 DD計算が`holding.get("current_value",0)`でポジション評価額が常に0 → v6.5akで時価計算に修正
- capital_flow_radar.pyがmacro_flow.jsonを全上書し → macro_dataフィールド消失 → v6.5akでread-modify-write修正
- Phase 3bが`self.pro_model`（CrewAI用LangChain）の`generate_content()`を呼び出し → `ModelFactory.get_genai_model("critical")`に修正

---

## 🏛️ TrinityCouncilフロー

```
[run_trigger.py 30秒サイクル]
  ├── Phase 0:    リスク検知 + 5層売却チェック（check_tp_sl_all_positions — Council非依存）
  │   ├── F2:     BTC急落リスク（30秒毎）
  │   │           └ L1: BTC -5% → SL引き締め(x0.5)
  │   │           └ L2: BTC -8% → 含み益利確
  │   │           └ L3: BTC -12% → 全ポジション緊急売却
  │   ├── F2b:    マクロ急変検知（30分キャッシュ — お盆FW即時版）
  │   │           └ L1: SPY -2% → SL引き締め
  │   │           └ L2: SPY -3% + Gold +1.5% → 含み益利確
  │   │           └ L3: SPY -5% + Gold +3% → 全ポジション緊急売却
  │   │           └ F2とF2bの最大レベルを採用
  │   ├── S2:     戦略書モニタリング（30分毎ログ）
  │   │           └ bull/bear進行度、bear70%警告、bull80%通知
  │   ├── S3:     シナリオ動的出口
  │   │           └ S3-1: 戦略SLで固定SL上書き（固定SLの2倍が安全上限）
  │   │           └ S3-2: bear trigger 70%接近でexit_profile引き締め
  │   │           └ S3-3: bull target 100%到達でトレール早期開始
  │   ├── 5層:    売却チェック（戦略別exit_profile: short/mid/long）
  │   │           └ 第1層: 固定SL（戦略別）
  │   │           └ 第2層: トレーリングTP（戦略別開始/ドロップ幅）
  │   │           └ 第2層b: 固定上限TP（戦略別）
  │   │           └ 第3層: RSI>閾値+利益1.5%
  │   │           └ 第4層: 時間制約（戦略別）
  │   └── E1:     SL/TP発火時 → 構造化内省（S4: 戦略比較+scenario_outcome+quality_score）
  │
  ├── Trigger: 2hローテーションCouncil（BTC→VIRTUAL→ETH タイムスタンプベース）
  │
TrinityCouncil v2
  ├── Phase 1〜1d-W: Scout偵察+オンチェーン+ACP参考+センチメント+記憶+Reflexion(E2)
  ├── Phase 1-P:  N.1ペアトレードシグナル注入（VIRTUAL/AIXBT相関分析）
  ├── Phase 1e:   PlanningCrew戦略リスク評価 + F5資本フローフェーズ判定
  ├── Phase 2:    Backtest 9戦略並列（gplearn含む）
  ├── Phase 3:    三者協議（Bull/Bear/Neo）
  ├── Phase 3b:   戦略書生成（Phase S1 — verdict=BUY時のみ）
  │              └ thesis/bull_scenario/bear_scenario/invalidation
  │              └ ATR基準SL/TP + 3%リスク制約 + RR比検証
  │              └ evidence品質チェック（≧3根拠+定量データ+risk_pct≦6%）
  │              └ evidence_snapshot自動付加
  ├── Phase 4:    JSONパース → verdict+confidence+key_factor抽出
  ├── Phase 4b:   スコアリングテーブル
  │              └ ニュートラル50起点
  │              └ bt/sent/acc → [既存]
  │              └ 時間帯スコア（EU+10/Asia-10）
  │              └ ナンピンペナルティ（2回以上-10）
  │              └ 連敗ペナルティ（SL 3連続-10、24h半減、48h完全解除）
  │              └ N.1ペアZ-score（±4〜±8）
  │              └ CFRマクロスコア（±2〜±10）
  │              └ F5 capital_flow_phase（+5〜-10）
  │              └ F1戦略信頼度スコア（±5）
  │              └ E3 EvolveR動的ルール（自動適用、±15上限）
  │              └ E2 Reflexion confidence調整（±10）
  ├── Phase 5:    ガード6段
  │              └ ① USDC下限15% → ② 銘柄上限30% → ②b Tier1合計50%
  │              └ ②c confidence≧50 → ②d ナンピン≦3回
  │              └ ③ confidence連動BUY額（3%/5%/7%/10%）
  │              └ BUY成功時 → entry_context + strategy保存
  ├── Phase 6:    Moltbook投稿（Self-Refine+agentfinance重点化）
  ├── Phase 7:    Discord報告（確信度・要因・戦略thesis表示）
  ├── Phase 8:    メモリ詳細保存 + Evaluator自動実行
```

---

## 🤖 自律サイクル

```
[neo-collector.service]
  5分ごと      → VIRTUAL/AIXBT/LUNA をDexScreenerから取得・SQLite蓄積
  60分ごと     → GeckoTerminal 4h足OHLCVキャンドル取得
  1日ごと      → 180日より古いデータを自動パージ + macro_collector日次実行

[neo-radar.service]
  30秒ごと     → F2 BTC急落チェック + F2b マクロ急変チェック(30分キャッシュ)
                 + S2 戦略書モニタリング + S3 動的出口 + 5層売却チェック
  2時間ごと    → 定期Council召集（BTC→VIRTUAL→ETHローテーション）
  60分ごと     → Alpha Sweep
  2時間ごと    → Moltbookエンゲージメント
  6時間ごと    → Performance Evaluator + Discordダッシュボード + CFR更新
  毎日JST02:00 → Nightly Batch（8ステップ + Voyager/EvolveR/gplearn/ACP宣伝）

[neo-resource-api.service]
  常時         → FastAPI port 8099

[neo-acp-seller.service]
  常時         → WebSocket接続でJob受付待ち
               └ graduation_complete ($2.00 + 実費×回数)
               └ graduation_boost ($0.50)
               └ offering_audit ($0.30)
               └ profile_seo ($0.30)
               └ （取引系6 offerings: Local保持・再登録可能）
```

---

## 🛡️ リスクヘッジ全レイヤー

```
【即時対応（30秒）】
  F2:   BTC急落 → L1(SL引き締め) / L2(含み益利確) / L3(全ポジション緊急売却)
  F2b:  SPY/Gold急変 → 同3段階（30分キャッシュ — BTC前の先回り検知）
  5層:  固定SL / トレーリングTP / RSI出口 / 時間制約（戦略別exit_profile）
  S3:   戦略SL上書き / bear接近で引き締め / bull到達でトレール早期化

【BUY時ガード（Phase 5）】
  USDC下限15% / 銘柄上限30% / Tier1合計50%
  confidence閾値50 / ナンピン回数制限MAX 3回
  confidence連動ポジションサイズ（3%/5%/7%/10%）

【Council時（2h毎）】
  Phase 4bルールベースconfidence（LLM上書き）
  F5 capital_flow_phase（マクロ環境 → RISK_OFF_EXIT=-10）
  CostGuard L1-L4（コスト/日次損失/連敗冷却/DD5%全ブロック）

【戦略レベル（Phase S）】
  Phase 3b: 戦略書のハード制約（3%リスク/risk_pct≦6%/ATR基準/RR≧1.5）
  S2: シナリオモニタリング（bull/bear進行度）
  S3: invalidation条件 → 戦略前提崩壊時アクション
  S4: 戦略内省 → scenario_outcome + quality_score蓄積

【自己進化】
  E1: 構造化内省（SL発火時 → failure_category + 戦略比較）
  E2: Reflexion（思考バイアス検出 → confidence調整）
  E3: EvolveR動的ルール（自動スコアリング調整）
  Voyager: パターン学習 / gplearn: 遺伝的プログラミング戦略進化
```

---

## 📁 重要ファイルパス

```
メインレーダー:       run_trigger.py
Council:             agents/trinity_council.py
PlanningAgent:       agents/planning_agent.py（F5資本フロー+戦略リスク評価）
PaperWallet:         tools/paper_wallet.py → data/paper_wallet.json
PortfolioManager:    tools/portfolio_manager.py
市場データSQLite:     vault/market_db/prices.sqlite
ModelFactory:        core/model_factory.py
CostGuard:           core/cost_guard.py（L1-L4サーキットブレーカー）
MacroCollector:      tools/macro_collector.py（F5 yfinance+CoinGecko日次）
CapitalFlowRadar:    tools/capital_flow_radar.py（CFRスコア6h更新）
F2bキャッシュ:        vault/blackboard/f2b_macro_cache.json
Voyager:             research/voyager_skills.py
EvolveR:             research/evolver_rules.py
N.1ペアトレード:      research/n1_pair_trade.py
H.2取引分析:          research/h2_trade_analysis.py
バックテスト:         research/backtests/run_backtest.py（9戦略）
gplearn:             research/gplearn_strategy.py
ACP offerings:       skills/virtuals-protocol-acp/src/seller/offerings/
ACP resources:       skills/virtuals-protocol-acp/src/seller/resources/
Resource API:        tools/neo_resource_api.py
FinBERTセンチメント:   tools/finbert_sentiment.py
クジラ監視:           tools/whale_monitor.py
Moltbook:            tools/moltbook_tool.py / moltbook_engager.py
マクロフロー:         vault/blackboard/macro_flow.json（CFR+macro_data+capital_flow_phase）
引き継ぎ白書:         docs/GSD計画_v*_引き継ぎ白書.md（最新版を使用）
アーキテクチャマップ:   ARCHITECTURE.md
⚠️ 空DB（使わない）:  data/market_data.db, data/neo_market.db
```

> 📌 詳細なファイル構成・依存関係・呼び出しフローは **ARCHITECTURE.md** を参照

---

## 🔧 システム状態クイックチェック

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 全サービス状態
for svc in neo-radar neo-collector neo-resource-api neo-acp-seller; do
    echo "$svc: $(systemctl is-active $svc.service)"
done

# 勝率・ポートフォリオ
./neo-env/bin/python -c "
import sys,json; sys.path.insert(0,'.')
from tools.paper_wallet import PaperWallet
pw = PaperWallet()
hist = pw.state.get('history', [])
buy_q = {}; wins = 0; losses = 0
for h in hist:
    s = h.get('symbol', '')
    if h['action'] == 'BUY': buy_q.setdefault(s, []).append(float(h['price']))
    elif h['action'] == 'SELL' and buy_q.get(s):
        if float(h['price']) > buy_q[s].pop(0): wins += 1
        else: losses += 1
total = wins + losses
print(f'取引: {len(hist)}件 | 決済: {total}ペア | 勝率: {wins/total*100:.1f}%' if total else 'N/A')
print(f'USDC: \${pw.state[\"usd_balance\"]:,.2f}')
for sym, data in pw.state.get('holdings', {}).items():
    amt = data['amount'] if isinstance(data, dict) else data
    print(f'  {sym}: {amt:.2f} tag={data.get(\"strategy_tag\",\"?\")} exit={data.get(\"exit_profile\",\"?\")}' if isinstance(data, dict) else f'  {sym}: {amt}')
"

# 最新ログ
tail -20 radar_output.log
```

---

## 🚨 緊急時コマンド

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace

# 全サービス再起動
for svc in neo-radar neo-collector neo-resource-api neo-acp-seller; do
    systemctl restart $svc.service
done

# Council手動テスト
./neo-env/bin/python -c "
import sys; sys.path.insert(0,'.')
from agents.trinity_council import TrinityCouncil
c = TrinityCouncil()
r = c.run(sentiment_score=0.5, context='手動テスト', target_symbol='VIRTUAL')
print(f\"verdict: {r.get('verdict')}, confidence: {r.get('confidence')}\")
"

# L4(DD)チェック
./neo-env/bin/python -c "
import sys; sys.path.insert(0,'.')
from core.cost_guard import CostGuard
cg = CostGuard()
ok, dd = cg.check_drawdown()
print(f'L4 approved: {ok}, DD: {dd:.2f}%')
"

# F2bマクロ急変キャッシュ確認
cat vault/blackboard/f2b_macro_cache.json 2>/dev/null | python3 -m json.tool || echo "キャッシュなし"

# F5マクロデータ確認
cat vault/blackboard/macro_flow.json | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'macro_data: {list(d.get(\"macro_data\",{}).keys())}'); print(f'capital_flow_phase判定用score: {d.get(\"score\",\"N/A\")}')"
```

---

## セッション終了時の作業

1. 白書を更新する（バージョン番号・日時・完了タスク・システム状態）
2. 構造変更があった場合は `ARCHITECTURE.md` も更新する
3. `git add -A && git commit` する
