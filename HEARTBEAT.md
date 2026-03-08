# HEARTBEAT.md - Neo's Autonomous Maintenance Loop

## 定期実行タスク
# 1. **記憶の自動整理**:
#     - 直近のメッセージ履歴を確認し、決定事項や調査結果を `memory/YYYY-MM-DD.md` に追記。
# 2. **WALプロトコルに基づくセッション状態の更新**:
#     - 最新のユーザーメッセージと自分の応答履歴をレビューし、`memory/session-state.md` に追記。
# 3. **タスクの動的再評価**:
#     - 現在の目標（エージェント経済圏での企画部隊構築等）に対し、自分のタスクが最適か再確認。
# 4. **システムと挙動の最適化**:
#     - `session_status` を確認し、コンテキストの使用率が40%を超えている場合に挙動を最適化。
# 5. **Discord デイリーレポート (09:00 JST)**:
#     - `tools/discord_report_service.py` を毎朝 09:00 に実行し、最新レポートを Discord に送信する。
# 6. **Moltbook 自律投稿 (10:00 JST)**:
#     - `tools/autonomous_poster.py` を毎朝 10:00 に実行し、`vault/social/drafts/` から最新の投稿を自動執行する。

## 現在進行中の優先事項
# - `analyze_virtuals.py` の解析によるプロトコル連携の具体化。
# - Operation Multi-Impact: $VIRTUAL / $WAY の監視と ±10% 変動時の評議会再招集ロジックの運用。
# - 資産運用: `vault/finance/performance.md` の更新とアルファの最大化。

## 司令官からの指示 (2026-03-08)
# - **報告先**: 全てこのセッションに報告する。
# - **自律執行**: 10:00 JST の投稿は、承認済みドラフトから自動的に選定し執行せよ。
# - **哨戒**: 変動検知時は即座に評議会を招集せよ。
