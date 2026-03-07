# Current Workspace Directory Map
Generated on: 2026-03-07
Purpose: Visual guide to the current project structure and file roles.

## Root Directory (`/data/.openclaw/workspace`)
| File/Directory | Role/Description |
| :--- | :--- |
| `neo_main.py` | **Main Entry Point**: Neoオーケストレーターの起動スクリプト（インタラクティブ/サービス）。 |
| `run_cycle.py` | **Autonomous Cycle Runner**: 定期的な自律サイクル（調査→計画→実行）を実行するスクリプト。 |
| `analyze_virtuals.py` | **Analysis Script**: Virtuals Protocolデータ分析用スクリプト（スポット分析用）。 |
| `requirements.txt` | **Dependencies**: Pythonパッケージの依存関係リスト。 |
| `package-installed.json` | **Package Log**: インストール済みパッケージの記録（npm等）。 |
| `*.md` (AGENTS, MEMORY, etc.) | **Documentation & Context**: AI人格、記憶、システムプロンプト等のコア定義ファイル。 |
| `.env` | **Environment Variables**: APIキーなどの機密情報（Git管理外）。 |
| `.env.example` | **Env Template**: `.env` のひな形。機密情報を空欄にしたもの。 |
| `.gitignore` | **Git Ignore**: Git管理から除外するファイルリスト（`.env` 等）。 |

## 📂 `agents/` (The Crew Roster)
*各専門エージェントの実装ファイル。*
| File | Role |
| :--- | :--- |
| `scout_crew.py` | **Ecosystem Scout**: トレンドや価格情報の収集を行うエージェント。 |
| `sentiment_crew.py` | **Sentiment Analysis**: 市場心理を分析するエージェント。 |
| `planning_crew.py` | **Strategic Planning**: リスク戦略の策定と指令を出すエージェント。 |
| `acp_executor_crew.py` | **ACP Executor**: オンチェーン取引（ACP）ペイロードを生成するエージェント。 |
| `content_creator_crew.py` | **Content Creator**: Moltbookへの投稿を生成するエージェント。 |
| `development_crew.py` | **Agent Development**: 自己修正やコードパッチを行う開発エージェント。 |
| `paper_trader.py` | **Paper Trading**: 架空資金での取引シミュレーションを行うロジック。 |

## 📂 `core/` (System Foundation)
*システム全体の基盤と設定。*
| File | Role |
| :--- | :--- |
| `config.py` | **Configuration**: LLM設定、APIキー、定数などを一元管理。 |
| `base_crew.py` | **Base Class**: 全エージェント共通のロジック、ログ記録、エラー処理。 |

## 📂 `bridge/` (Interoperability)
*異なるシステムやプロトコル間の接続。*
| File | Role |
| :--- | :--- |
| `crewai_bridge.py` | **CrewAI Adapter**: CrewAIフレームワークへのインターフェース。 |
| `acp_schema.py` | **ACP Protocol**: ACP（Agent Communication Protocol）のスキーマ定義。 |

## 📂 `tools/` (Agent Capabilities)
*エージェントが使用する具体的な機能モジュール。*
| File | Role |
| :--- | :--- |
| `market_data.py` | **Market Data**: DexScreener等から価格・出来高データを取得。 |
| `credit_score.py` | **Credit Scoring**: 信用格付けロジックの実装。 |
| `moltbook_tool.py` | **Social Media**: Moltbookへの投稿インターフェース。 |
| `crypto_data.py` | **Crypto Info**: 一般的な暗号通貨データの取得。 |
| `data_fetcher.py` | **Generic Fetcher**: Webリクエスト等の汎用データ取得ユーティリティ。 |
| `paper_wallet.py` | **Wallet Sim**: ペーパートレード用ウォレットの状態管理。 |
| `memory_hygiene.py` | **Memory & Context Compression**: メモリ整理・最適化・動的コンテキスト圧縮ツール。 |
| `gsd_tool.py` | **GSD Adapter**: Get-Shit-DoneフレームワークのPythonラッパー。仕様駆動開発フローを実行。 |

## 📂 `tests/` (Test Suite)
*ユニットテストおよび統合テスト。*
| File | Role |
| :--- | :--- |
| `test_paper_trade.py` | **Paper Trade Test**: ペーパートレード機能の動作確認用スクリプト。 |
| `test_context_management.py` | **Context Test**: コンテキスト圧縮機能の動作確認用スクリプト。 |
| `test_gsd_integration.py` | **GSD Workflow Test**: GSDツールの初期化・計画・実行フローの動作確認。 |

## 📂 `data/` (State & Cache)
| File | Role |
| :--- | :--- |
| `paper_wallet.json` | **Wallet State**: ペーパートレードの残高情報を保持するJSON。 |
| `market_cache_VIRTUAL.json` | **Data Cache**: APIコール削減のための市場データキャッシュ。 |

## 📂 `libs/` (External Dependencies)
| File | Role |
| :--- | :--- |
| `virtuals-sdk/` | **SDK**: Virtuals Protocol SDK（ローカルコピーまたはサブモジュール）。 |

## 📂 `logs/` (System Records)
* `execution_history.jsonl`: メイン実行ログ。
* `market_cycle.jsonl`: 自律サイクルの構造化データログ。
* `crewai/*.json`: エージェント実行ごとの詳細ログ。

## 📂 `memory/` (Long-Term Storage)
* `YYYY-MM-DD.md`: 日次運用ログ。
* `crewai_db/`: CrewAI用のベクターストアまたは永続化データ。

## 📂 `skills/` (OpenClaw Skills)
* `agent-orchestration/`, `proactive-agent/`, etc.: OpenClawにインストールされたスキル群。
* `get-shit-done/`: GSDフレームワークのプロンプトと設定。
