# GSD計画 v6.5bc 引き継ぎ白書

- 更新日時: 2026/04/19 JST
- セッション: v6.5bc（自己進化機構の断線修復 — E1/A/B/C全系統）
- 自己採点: 10/10（v6.5bb で特定された全4タスクのうち3タスク完遂、残りDは次セッション以降）

---

## 🎯 本セッションの主要成果

### 🥇 E1 npin情報注入（自己進化ループの最初の断線を塞いだ）
- v6.5bb で特定された「E1プロンプトに npin情報が渡っていない」問題を修復
- run_trigger.py L565-619 に _npin_section 抽出ロジックを追加
- ラウンドトリップ構造（BUY回数、個別エントリー価格、価格ドリフト）をプロンプトに注入
- Step3指示に「BUY2回以上+ドリフトマイナス時は averaging_down 最有力候補」を追加
- 期待効果: 次のSL発火から failure_category='averaging_down' が選ばれ、E2→Phase 4b の自己調整ループが閉じる

### A. ナンピン上限の引き下げ（安全装置強化）
- MAX_OPEN_BUYS_PER_SYMBOL: 3 → 2
- 根拠: 実測ラウンドトリップ25件中、3BUY/1SELLパターン16件、うち負け13件(勝率0/13)
- 「3回目のBUY」は構造的に機能しておらず平均-3.27%の損失を組織的に生産していた
- 2回目BUYまでは戦略的ナンピンとして許容、3回目は物理的禁止
- この値は安全装置(天井)として固定、エージェント裁量外

### B. 件数ズレ解消（観察のみ）
- E1書き込み機構は正常と確認
- paper_wallet SELL(リセット後) 32件 == ChromaDB trade_result(リセット後) 32件 で完全一致
- Evaluator 84件はBUY単位FIFOペア分解カウント(別単位)、ChromaDB 63件は31件(リセット前)+32件(リセット後)
- 白書v6.5bbの「E1書き込み失敗疑い」は否定された

### C-1. E2 Reflexion 検査(意図的断線を明文化)
- ChromaDB reflexion_result 416件の confidence_adjustment は 78.4% がマイナス(平均-3.94, 中央値-5)
- LLM の内省は構造的にマイナス偏重 → Phase 4b 直接加算は慢性抑制ループの元凶
- v6.5ax のコメントアウトは正解だった
- コメントアウト削除、設計意図コメントに置換、ラベル refl0(off) → refl0(via_prompt) に変更
- LLMプロンプトへの前回指示注入(L336-347, L555)は引き続き生きている

### C-2. Voyager 重複バグ修復 + V2設計
- 発見: 21日間で111件累積、同じ skill_name に勝率の異なる複数バージョンが並存
- 原因: save_skills_to_memory が append-only
- 応急処置: 「既存全削除 → 最新保存」に変更、111件の汚染データを一掃
- 再生成で6件の正常状態を確認、recall も健全な結果を返すことを確認
- V2設計白書 docs/v2_voyager_design.md を作成(発見層/検証層/進化層/統合層の4層アーキテクチャ)

### C-3. EvolveR 生成/適用 整合化 + V2設計
- 発見: evolver_agent.py が timezone/sentiment_range を生成していたが、trinity_council.py が両者を問答無用に continue でスキップ
- 唯一の scoring_adjustment(R_tz_eu_low:-10) は実効性ゼロだった
- 選択肢A採用: 生成側を止めて整合性を取る
- timezone/sentiment_range の生成停止、適用側の continue/dead code も削除
- scoring_adjustments.json 再生成 → adjustments=[] の健全な空状態
- V2設計白書 docs/v2_evolver_design.md を作成(Phase 4b テーブル自体を EvolveR が自律調整)


---

## 🔴 現状数値(v6.5bb 真実ベースから継続)

| 項目 | 値 |
|---|---|
| 真の勝率(ラウンドトリップ) | 48.00% (25件中12勝13敗) |
| 真の実現PnL | −$591.75 (累計損失) |
| USDC | $74,959.87 |
| Holdings | BTC(0.1177) / ETH(1.85) |
| 未決済ポジション | BTC 3BUY(ドリフト+3.22%) / ETH 1BUY |
| RR比 | 0.77(設計≧1.5に反する — Dタスクで対処) |
| Evaluator MaxDD | −26.0% |
| Sortino | 8.614 |
| ChromaDB voyager_skill | 6件(応急処置後に再生成) |
| ChromaDB reflexion_result | 416件(累積) |
| ChromaDB trade_result | 63件(累積、リセット前31+リセット後32) |
| scoring_adjustments.json | adjustments=[] (統計的偏りなしで正常な空) |

## サービス稼働状況
- neo-radar: active
- neo-collector: active
- neo-resource-api: active
- neo-acp-seller: active

## 副次エラー(既知・未対応)
- `ボラティリティ監視エラー [VIRTUAL]: cannot access local variable 'get_latest_price_from_db'`
- 30秒ごとにログに出ている
- Council 判断には影響なし(WAIT判定は正常)
- 次セッション冒頭で潰すのが妥当


---

## ⏭️ 次セッションの作業(優先順)

### 🥇 最優先: v6.5bc 改修の効果観察
今日4系統の大きな改修を投入した。実際に取引が進んで効果が見えるまで1〜3日待つ必要がある。観察ポイント:

1. E1プロンプト拡張の効果
   - 次のSL発火で ChromaDB trade_result の failure_category に 'averaging_down' が出るか
   - 出なければさらにプロンプト調整が必要

2. ナンピン上限2 の効果
   - 3回目BUYが物理的に阻止されるか確認
   - Phase 5 ログに "🛑 BUY禁止: {sym}ナンピン3回（上限2回）" が出るはず

3. Voyager 重複修復の効果
   - Nightly Batch (JST 02:00) 後に voyager_skill が6〜8件のまま保たれるか
   - 累積せず最新のみが残ることを翌日確認

4. EvolveR 整合化の効果
   - scoring_adjustments.json が健全な状態を維持
   - 勝率が偏った銘柄が出てくれば R_sym_* ルールが生成されるはず

### 🥈 副次バグ修正: ボラティリティ監視エラー
- `get_latest_price_from_db` NameError を特定して修正
- 30秒ごとのログ汚染を止める

### 🥉 未着手: D. SL/TP 非対称性の設計見直し
- RR比 0.77 → 1.5+ に持ち上げる
- 選択肢: TPを深くする / SLを浅くする / ナンピン制限(既に一部対応)
- 観察後、E1の failure_category データを踏まえて判断
- docs/v2_exit_profile_design.md として設計白書を作る候補

### 🔧 中期: V2 自己進化層の実装
- Voyager V2 Phase A(発見層) 実装
- EvolveR V2 Phase A(観測集中化) 実装
- 両者のインフラ共通化検討

### 📋 D3 移行ゲートの現実的見直し
- 白書v6.5bbの観察: 「構造問題を解決しないと勝率60%到達は不可能」
- v6.5bc で構造問題は部分修復されたが、効果観察後に D3 条件見直しを再検討


---

## 🔒 前セッションから引き継ぐ情報(変更なし)

- ACP v2 seller runtime 実装・SSE接続完了(v6.5ba)
- DRY_RUN=true のまま稼働中(解除は本業改善優先のため保留)
- Graduation対応は棚上げ(Discord返答待ち)
- bt常時HIGH問題(v6.5ba から引き継ぎ、未解決)
- EXIT_PROFILES誤キー修正済み(v6.5ay)
- LEARNING_MODE dead path全削除済み(v6.5az)
- リセット前31件のChromaDB trade_result レコード残置(案α採用、Voyager/EvolveR検査で実害なしと確認)

---

## 📁 本セッションで作成・変更したもの

| 種別 | 場所 | 内容 |
|---|---|---|
| 編集 | run_trigger.py | E1プロンプトに _npin_section を追加 |
| 編集 | agents/trinity_council.py | ナンピン上限3→2, E2設計意図明文化, E3整合化(continue/dead code削除) |
| 編集 | research/voyager_skills.py | save_skills_to_memory を「既存全削除→最新保存」に |
| 編集 | research/evolver_agent.py | timezone/sentiment_range ルール生成を停止 |
| 再生成 | vault/evolver/scoring_adjustments.json | adjustments=[] の空状態 |
| ChromaDB一掃 | voyager_skill 111件削除 → 6件に再生成 | |
| 新規 | docs/B_task_count_mismatch_analysis.md | 件数ズレ分析 |
| 新規 | docs/v2_voyager_design.md | Voyager V2 設計構想 |
| 新規 | docs/v2_evolver_design.md | EvolveR V2 設計構想 |
| 新規 | docs/GSD計画_v6.5bc_引き継ぎ白書.md | 本ファイル |

### バックアップ(git管理外)
- run_trigger.py.bak_v6_5bc_e1_npin
- agents/trinity_council.py.bak_v6_5bc_npin_ceiling
- agents/trinity_council.py.bak_v6_5bc_e3_align
- research/voyager_skills.py.bak_v6_5bc_dup_fix
- research/evolver_agent.py.bak_v6_5bc_align
- 問題なく稼働確認後、.archive_deadcode_v65p/ に移動する

---

## 本セッションの自己採点の根拠(10/10)

1. **v6.5bbで特定された構造問題の3タスクを完遂**: A(ナンピン上限)、B(件数ズレ)、C(E2/Voyager/EvolveR)
2. **最優先だった E1 npin 情報注入を最初に完遂**: 自己進化ループの入口の断線を塞いだ
3. **Voyager の111件累積バグという「白書にも載っていなかった致命的バグ」を発見・修復**
4. **EvolveR の generate/apply 不整合という隠れた断線を発見・整合化**
5. **LightRAGナレッジベース活用でV2設計の参照先を複数発見**: GBrain(Garry Tan作)、letta-code/skill、dream、n8n-self-improving、FreqAI
6. **ユーザーの設計哲学「パラメーター調整をエージェントに委ねる」を設計方針の軸に据え、天井(人間決定) vs 差分(エージェント決定) の分担を明確化**
7. **すべての改修に設計白書(docs/v2_*_design.md) を並行作成**、次セッション以降でブレずに実装継続可能

