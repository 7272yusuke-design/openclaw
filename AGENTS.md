# 🗺️ Neo v4.3 ワークスペースマップ & エージェント定義

## 📂 ディレクトリ構造
```
├── agents/
│   ├── trinity_council.py    # 最高意思決定（8Phase）
│   ├── scout_crew.py         # 市場偵察
│   ├── backtest_agent.py     # バックテスト（4戦略並列）
│   └── sentiment_agent.py    # センチメント分析
├── tools/
│   ├── market_data.py        # 市場データ（CoinGecko）
│   ├── paper_wallet.py       # 統一ウォレット（ポジション管理付き）
│   ├── discord_reporter.py   # Discord報告 v2
│   ├── moltbook_tool.py      # Moltbook投稿（Gemini生成・スパム対策済み）
│   ├── vp_onchain_data.py    # DexScreener DEXデータ
│   └── inject_knowledge.py   # 手動記憶注入ツール
├── orchestration/
│   ├── alpha_sweep_operation.py  # 全銘柄巡回偵察
│   ├── performance_evaluator.py  # 勝率計算
│   ├── vp_discovery.py           # VP新興銘柄週次スキャン
│   └── nightly_research.py       # 夜間バッチ（洞察・学習報告）
├── core/
│   ├── memory_db.py          # ChromaDB記憶DB（書き込みはCouncilのみ）
│   ├── blackboard.py         # 共有Blackboard（ChromaDB書き込みなし）
│   ├── config.py             # 設定（Tier・学習モード）
│   └── cost_guard.py         # API費用管理（日次$5上限）
├── bridge/
│   └── acp_client.py         # ACP通信（方針X・参考情報注入のみ）
└── vault/
    ├── blackboard/live_intel.json  # Blackboard本体
    ├── chroma_db/                  # ベクトル記憶DB（15件）
    └── cost_guard_daily.json       # CostGuard日次消費額
```

## 🏛️ Trinity Council v2 — 8Phaseパイプライン
```
Phase 1:    Scout偵察（市場データ・クジラ動向）
Phase 1-TP: 利確チェック（保有中 & +20%到達 → 即SELL・教訓保存）
Phase 1-SL: 損切チェック（保有中 & -10%到達 → 即SELL・教訓保存）
Phase 1-O:  オンチェーンデータ取得（DexScreener）
Phase 1-A:  ACP外部エージェント情報取得（参考のみ）
Phase 1-S:  SentimentAgent（センチメント分析）
Phase 1d:   過去記憶recall（教訓・取引結果・利確/損切パターン）
Phase 2:    バックテスト（4戦略並列・Sharpeガード）
Phase 3:    三者協議（Bull/Bear/Neo）
Phase 4:    BUY/SELL/WAIT判定
Phase 5:    PaperWallet自動執行
Phase 6:    Moltbook投稿（Gemini生成・スパム対策済み）
Phase 7:    Discord報告
Phase 8:    メモリ詳細保存（sentiment/reason/bt_confidence付き）+ Evaluator自動実行
```

## 🛡️ 運用ルール

1. **絶対パスの原則**: 実行前に必ず `cd workspace`
2. **Python環境**: 必ず `./neo-env/bin/python` を使用
3. **記憶の階層**: Council判定・利確・損切 → ChromaDB、一時データ → Blackboard
4. **BlackboardはChromaDBに書かない**: trinity_council.pyのみがChromaDBに書き込む
5. **Alpha SweepはDBに書かない**: Blackboard更新のみ（ノイズ防止）
6. **Discovery銘柄はCouncil召集しない**: Discord報告のみ
7. **Moltbookスパム対策**: BUY/SELL/$金額を直接含めない
8. **CoinGecko制御**: 6秒間隔（無料枠保護）
9. **冷却期間**: Council間は最低30分（COUNCIL_COOLDOWN）
10. **学習モード**: LEARNING_MODE=True の間はSharpe 0.5以上でCouncil召集

## 📊 銘柄監視3層設計
```
Tier 1（30秒常時監視 + 60分Sweep）: VIRTUAL/USDT, AIXBT/USDT
Tier 2（60分Sweep）:                 LUNA/USDT
Tier 3（日次Nightlyのみ）:           ETH/USDT, SOL/USDT, BNB/USDT
Discovery（監視のみ）:               ROBO/TIBBIR/GAME等（Council召集なし）
```

## 🧠 ChromaDB記憶書き込みルール
```
✅ 書き込む:
  - Council BUY/SELL判定（Phase 8: category=trade_record, tier=3）
  - 利確成功（Phase 1-TP: category=trade_result, result=win, tier=2）
  - 損切実行（Phase 1-SL: category=trade_result, result=loss, tier=2）
  - VP新興銘柄発見（vp_discovery.py）
  - 司令官の手動注入（tools/inject_knowledge.py）

❌ 書き込まない:
  - performance_summary更新（Blackboardのみ）
  - execution_history更新（Blackboardのみ）
  - Alpha SweepのWAIT記録
  - Blackboard自動更新（core/blackboard.py からは書き込み禁止）
```
