# Project: GSD Parallel Execution Engine

## Context
現在のNeoシステムは、GSDロードマップ上のタスクを上から順にシーケンシャル（直列）に実行しています。しかし、多くの開発タスクや調査タスクは相互に依存しておらず、並列実行が可能です。現在の直列モデルは、LLMの待ち時間を累積させ、全体の完了時間を不必要に延ばしています。

## Goal
GSDロードマップ（ROADMAP.md）を解析し、依存関係のない「実行可能なタスク」を動的に特定する「並列処理エンジン」を実装する。これにより、複数のエージェントが同時に異なるタスクに取り組めるようにし、システム全体の処理速度を大幅に向上させる。

## Requirements
1. **Dependency Metadata**: ROADMAP.md の各タスクに `[Depends on: ID]` 形式のメタデータを付与する。
2. **Parser**: Markdownを解析し、タスクの依存関係グラフ（DAG）を構築するロジック。
3. **Async Dispatcher**: 依存関係が解決されたタスク群を CrewAI の `async_execution=True` タスクとして一括発行する機能。
4. **Backward Compatibility**: 既存のロードマップ形式も（依存関係なしとして）扱えること。
