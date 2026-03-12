# 🗺️ Neo ワークスペース・マップ & 兵令

## 📂 ディレクトリ構造 (The Terrain)
/docker/openclaw-taan/data/.openclaw/workspace/
├── agents/             # 🧠 知能部隊 (CrewAI Agents)
│   ├── trinity_council.py  # 最高司令部（意思決定の核）
│   ├── scout_agent.py      # 偵察部隊（クジラ・テクニカル検知）
│   └── backtest_agent.py   # シミュレーション部隊（検証）
├── core/               # ⚙️ システム基盤 (Base Class, DB)
├── tools/              # 🛠️ 実行ツール (Discord, Moltbook, BacktestEngine)
├── vault/              # 📦 貯蔵庫 (DBデータ, マーケットCSV, チャート画像)
└── logs/               # 📜 監視記録 (daemon.log)

## 🛡️ 兵令（運用ルール）
1. **絶対パスの原則**: すべてのファイル参照は絶対パスで行う。
2. **非バッファ出力**: `python3 -u` でログのリアルタイム性を確保する。
3. **記憶の継承**: 重要な判断は必ず ChromaDB に store し、recall 可能にする。
