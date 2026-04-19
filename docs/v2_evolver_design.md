# V2 EvolveR 設計構想

- 作成日: 2026/04/19 v6.5bc
- ステータス: 設計段階（実装は次セッション以降）
- 関連: docs/v2_voyager_design.md / GSD計画_v6.5bb_引き継ぎ白書.md

---

## 背景: v1 EvolveR の構造的不整合

### v6.5bc 断線検査で発見した問題

v1 EvolveR は generate (evolver_agent.py) と apply (trinity_council.py L831-880) が別々のファイルで管理されており、両者のルールタイプ定義が食い違っていた:

| ルールタイプ | 生成側 | 適用側 | 実質 |
|---|---|---|---|
| timezone | 生成あり | continue で問答無用スキップ | 二重計上を避けるためのスキップだが、生成側も止めるべきだった |
| sentiment_range | 生成あり | continue で問答無用スキップ | 同上。加えて condition の意味も不整合だった |
| symbol | 生成あり | 適用あり | ✅ 健全 |
| bt_confidence | 生成あり | 適用あり | ✅ 健全 |
| capital_flow_phase | 生成なし | 適用あり | dead code |

結果: scoring_adjustments.json には唯一 timezone ルール1件が入っていたが、適用側で問答無用にスキップされ実効性ゼロ。EvolveR は動いているように見えて「何も反映されていない」状態だった。

### v6.5bc 応急処置
- evolver_agent.py で timezone / sentiment_range ルール生成を停止
- trinity_council.py の continue / dead code を削除、適用側を symbol / bt_confidence / capital_flow_phase の3種類に整理
- scoring_adjustments.json を再生成 → 現在は adjustments=[] の健全な空状態
- EvolveR は「強い偏りがあれば symbol or bt_confidence で調整」の最小機能として機能

---

## v1 の根本的な設計思想の問題

現状の EvolveR は「統計的に偏ったパラメーターを見つけて Phase 4b に ±5〜±15 を加算する」仕組み。でもこれは Phase 4b のスコア計算 **に調整値を足すだけ** で、Phase 4b 自体（固定テーブル TZ_SCORE_ASIA=-10 など）は一切変わらない。

つまり v1 は「固定テーブル + 動的調整の差分加算」という二層構造。

## 設計哲学との比較

ユーザー希望「パラメーター調整項目を極力エージェントに移行」と照らすと:
- 現状の TZ_SCORE_ASIA=-10 などは config.py のハードコード
- EvolveR はその外側で差分調整しているだけ
- 理想: **TZ_SCORE テーブル自体を EvolveR が書き換える**

---

## V2 の思想 — Phase 4b テーブルそのものの自律調整

### 基本コンセプト

現状:
- config.py: TZ_SCORE_ASIA / TZ_SCORE_EU / TZ_SCORE_US (固定値)
- EvolveR: 差分を別ファイルに出して trinity_council で加算

V2:
- EvolveR が Phase 4b の全スコア定数（TZ_SCORE_*, NPIN_PENALTY, CFR_SCORE 係数, MACRO_SCORE 係数...）を定期的に見直し、data-driven で更新
- config.py の値はあくまで初期値（cold start 用）
- 運用が進むにつれて現実のデータに適応した値に収束
- 「ハードコードしたパラメーターがエージェントに浸食される」

### 参照ナレッジ

| ナレッジ | 採用する思想 |
|---|---|
| n8n-self-improving-workflow-agent-l2c | Evaluator + Evolver で A/Bテスト → 勝者置換 |
| FreqAI (FreqTrade) | Hyperopt によるパラメーター最適化 |
| letta-code /skill | 繰り返しパターンを自動スキル化 |

### アーキテクチャ案

1. 観測層: 全ルール（tz/symbol/bt/macro/cfr...）の実績勝率を継続集計
2. 提案層: 実績と現在のスコア定数を比較し、LLM が改訂案を生成
3. A/Bテスト層: 改訂案を shadow mode で並行評価（本番はまだ旧テーブル）
4. 昇格層: 改訂案の成績が既存を上回れば本番テーブルに反映
5. 永続化: config.py ではなく vault/evolver/phase4b_table.json に管理

---

## 実装優先順位

### Phase A: 観測の集中化（次セッション想定）
- Phase 4b で加算される各スコア要素（tz/npin/cfr/macro/sentiment）を scoring_breakdown に詳細記録（既に部分的にある）
- 各要素別の過去30日勝率を evolver_agent.py で定期集計

### Phase B: 提案層
- LLM に「この要素は勝率XX%だが +10点の加算がある。妥当か?」を問わせる
- 提案は vault/evolver/proposed_table.json に

### Phase C: A/Bテスト層
- shadow モードで並行評価
- 実取引は現行テーブルのまま、提案テーブルで仮想的に confidence を計算
- 勝率が改善するかを観察

### Phase D: 昇格層
- 改善が認められれば config.py から動的テーブルへ移行
- config.py は「初期値ファイル」に降格

---

## Voyager V2 との関係

Voyager V2 と EvolveR V2 は姉妹関係:
- Voyager V2: スキル（条件付きパターン）の発見・進化
- EvolveR V2: スコアリング定数の自律調整
- 両者ともに n8n-self-improving パターンの Evaluator + Evolver を踏襲

将来的にはこの2つを統合した "Neo 自己進化層" として一本化することも可能。

---

## リスクと注意点

1. 初期データ不足: 14日程度だと偏りがあっても統計的有意に至らない → サンプル閾値を設ける
2. オーバーフィット: 直近データに過度適合 → 時間減衰ウィンドウ（90日など）を設ける
3. テーブル爆発: 全定数を可変化するとデバッグが困難 → まず TZ_SCORE_* と NPIN_PENALTY の2系統のみで実験

---

## 設計哲学との整合性

ユーザー希望「パラメーター調整項目を極力エージェントに移行」との照合:
- TZ_SCORE_* を EvolveR が調整: OK
- NPIN_PENALTY を EvolveR が調整: OK
- MAX_OPEN_BUYS_PER_SYMBOL（物理上限）: こちら側決定のまま（天井）

つまり天井は人間、差分調整はエージェント、という分担。

---

## 次のアクション

次セッション開始時:
1. この白書と docs/v2_voyager_design.md を確認
2. Voyager V2 と EvolveR V2 のどちらを先にやるか判断（Voyager V2 Phase A がシンプルなので先）
3. 両者のインフラ（shadow モード、提案ファイル形式）は共通化を検討
