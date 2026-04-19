# V2 Voyager 設計構想

- 作成日: 2026/04/19 v6.5bc
- ステータス: 設計段階（実装は次セッション以降）
- 関連: docs/B_task_count_mismatch_analysis.md / GSD計画_v6.5bb_引き継ぎ白書.md

---

## 背景: v1 Voyager の致命的欠陥

### 発見したバグ（v6.5bc 応急処置で止めた）
- 書き込みが append-only → 21日間で111件累積
- 同じ skill_name が複数バージョン並存（勝率 67% → 44% → 69% と3つ同時）
- LLM が矛盾する「教訓」を見て判断混乱
- Council の recall は時刻フィルタなし → 古いスキルが選ばれる可能性

### 応急処置（v6.5bc 完了）
- save_skills_to_memory を「既存全削除 → 最新保存」に変更
- 111件の汚染データを ChromaDB から一掃
- これはバグ修正であって「進化の仕組み」ではない

### v1 の根本的な設計思想の問題

現状の Voyager は:
- 人間が定義した7種類のスキル名に固定（asia/eu/us_session, rsi_exit, stop_loss_exit, symbol_trade_pattern）
- H.2分析の結果をそのまま保存するだけ
- 発見も検証も進化もない「履歴スナップショット」に過ぎない

つまり今の Voyager は自己進化システムではなく日次レポート。
白書の「Voyager: 7パターンスキル」はこの構造を正確に反映している。


---

## V2 の思想 — 真の自己進化ループ

### 参照する外部ナレッジ（LightRAG L1-external で発見）

| ナレッジ | 採用する思想 |
|---|---|
| letta-code /skill command | 繰り返しパターンをLLMが自動スキル化 |
| dream (Claude Code skill) | 重複排除・統合で記憶を整理 |
| n8n-self-improving-workflow-agent-l2c | Evaluator + Evolver で A/Bテスト → 勝者置換 |
| GBrain (Garry Tan作・4800★) | OpenClaw 向け長期記憶バックエンド（将来） |
| FreqAI (FreqTrade) | 機械学習ベースの戦略最適化 |
| Voyager (Minecraft元論文) | カリキュラム学習 + コードライブラリ蓄積 |

### 4層アーキテクチャ

1. 発見層（Discovery）: LLMが取引履歴から新パターン候補を発見。人間定義の7種類に縛られない
2. 検証層（Validation）: バックテストor Paper forward test。勝率/PnL/Sortinoで性能評価
3. 進化層（Evolution）: A/B比較 既存vs新候補 → 勝者のみ昇格。劣化したスキルは休眠化
4. 統合層（Consolidation）: 重複・類似スキルを定期統合。低パフォーマンス長期保持をアーカイブ（dream相当）


---

## 各層の詳細設計

### 1. 発見層（Discovery）

目的: 人間が定義していないパターンを LLM に発見させる

実行: 週次（日曜深夜の Nightly Batch 拡張）

入力: 過去30日の paper_wallet.history + ChromaDB trade_result

LLM プロンプト案（要約）:
- あなたは取引パターン発見エージェント
- 過去30日の取引履歴から「勝率が偏って高い/低い条件」を最大5個発見せよ
- 各発見に含めるもの: 条件（複数シグナルのAND/OR組み合わせ可）／サンプル数（最低5件）／勝率／仮説（なぜこの条件で勝率が偏るか）
- 例: RSI<35 かつ BTC 24h変動 +2%以上 かつ アジア時間 → 8件中7勝（仮説: 下落相場終わりのアジア時間押し目買い）

出力: category="voyager_hypothesis" として ChromaDB に保存（まだ本番未反映）

### 2. 検証層（Validation）

目的: 仮説候補をバックテストで定量検証

実行: 発見層の直後

ロジック:
- 各仮説を research/backtests/run_backtest.py と同様のエンジンで過去60日にバックテスト
- 合格基準: 勝率 ≧ 55% AND サンプル ≧ 10件 AND Sortino ≧ 1.0

出力: 合格した仮説のみ voyager_candidate に昇格


### 3. 進化層（Evolution）

目的: 既存スキルと新候補を比較し、勝者のみ採用

実行: 検証層の直後

ロジック:
- 各新候補について、類似既存スキルを similarity_search で検索
- 類似既存がない場合: 新規追加 → voyager_skill
- 新候補の score が 類似既存の score × 1.1 を超える場合: 既存を voyager_skill_archive に移動し、新候補を voyager_skill に昇格（10%以上の改善を要求）
- それ以外: 新候補を voyager_skill_rejected へ（学習履歴として保持）

スキルに追加するメタデータ:
- performance_score: 勝率 × (1 + Sortino/10)
- sample_size: 検証サンプル数
- discovered_at: 発見日
- last_validated_at: 最終検証日
- consecutive_wins_since_added: 昇格後の連勝数
- status: active / dormant / archived
- superseded_by: 置き換えられた場合の新スキルID

### 4. 統合層（Consolidation / dream）

目的: 類似スキル統合 + 低パフォーマンスアーカイブ

実行: 月次

ロジック:
- 全 active スキルを類似度で比較（コサイン類似度 > 0.85）
- 類似スキルペアを LLM に渡し「統合可能か？」判定
- 統合可能 → 新スキル生成、元2つは archived に
- 30日間サンプルが増えていないスキル → dormant
- 60日間 dormant → archived
- archived は削除ではなく別 category に移動（履歴保持）


---

## 実装優先順位

### Phase A: 最小実装（次セッション想定）
- 発見層のみ実装（Nightly の voyager_skills.py 拡張）
- LLM にパターン発見させ、提案を voyager_hypothesis に保存するだけ
- Council は現行スキル + 新候補の両方を LLM プロンプトに注入（参考情報として）

### Phase B: 検証層追加
- バックテスト統合
- voyager_candidate へ自動昇格

### Phase C: 進化層
- A/B比較ロジック
- スキルのバージョニング（performance_score/status）

### Phase D: 統合層
- 月次の dream 相当処理

---

## 既存システムへの影響

### trinity_council.py:928-933 の recall 呼び出し
- 現状: where category=voyager_skill のみ
- V2: where に status=active を追加

### get_relevant_skills の再設計
- 銘柄フィルタはすでに実装済み（汎用スキルは全銘柄に渡る）
- V2 では performance_score で降順ソート → 上位N件に絞る

### データ移行
- 現行の voyager_skill レコードに status=active, performance_score を後付けで計算
- 過去の trade_result 63件から性能を遡及計算


---

## リスクと注意点

1. LLM 発見のノイズ: 過度に複雑な条件を発見しがち → プロンプトで「シンプル・検証可能・閾値明示」を要求
2. バックテストのオーバーフィッティング: 過去60日で勝率55%でも未来は未知 → Forward test も併用
3. スキル爆発: 発見を無制限に受け入れるとスキル数が膨張 → アクティブ上限20件を設定
4. Council プロンプトへの量: V2 で候補が増えると LLM コンテキスト圧迫 → 上位3〜5件に絞る機構が必須

---

## 設計哲学との整合性

ユーザー希望「パラメーター調整項目を極力エージェントに移行」との照合:
- スキル定義を人間から LLM に移行（発見層）: OK
- スキル採用/棄却を A/B テストで自動判断（進化層）: OK
- スキル統合も LLM が判断（統合層）: OK

固定パラメーター（こちら側決定）として残すもの:
- 合格基準（勝率55% / Sortino 1.0 / サンプル10件）
- アクティブスキル上限数（20件）
- 性能改善の閾値（10%以上）
- 休眠化/アーカイブ化の期間（30日/60日）

これらは「エージェントの能動的調整が必要ない天井」であり、設計哲学と整合。

---

## 次のアクション

次セッション開始時:
1. この白書を確認
2. Phase A（発見層のみ）から着手
3. 1週間運用して発見されたパターンの質を評価
4. 評価次第で Phase B〜D を進める
