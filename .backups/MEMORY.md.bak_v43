# MEMORY.md — Neo Long-Term Memory Index
> **最終更新**: 2026-03-14（司令部による記憶整理後）
> **記憶DB**: ChromaDB (`vault/chroma_db/`) — 17件のクリーンな記憶
> **旧MEMORY.md**: このファイルはインデックスのみ。詳細記憶はChromaDBに格納。

---

## 📌 記憶の分類と保持方針

### Tier 1: 永久保持（教訓・原則）
| 日付 | 内容 |
|---|---|
| 2026-02-18 | Discord スパムフィルタの教訓（シャドウブロック発生条件） |
| 2026-03-12 | 司令官の特別教訓：クジラ「Accumulating」サインのダマシ対策 |
| 2026-03-12 | Moltbook投稿ルール：最低2.5分間隔 |
| 2026-03-12 | .envパースエラー対策：環境変数は常にクリーンに |
| 2026-03-12 | Git 100MB制限：neo-env/バイナリは.gitignore必須 |

### Tier 2: 参照用（アーキテクチャ変遷）
| 日付 | 内容 |
|---|---|
| 2026-02-17 | Virtual Protocol学習計画（初期目標設定） |
| 2026-02-25 | Neo 2.0 "The Commander" 始動 |
| 2026-03-04 | Neo v3.0 Hybrid Architecture（適材適所モデル構成） |

### Tier 3: 日次ログ（2026年2月）
- 2/18〜2/28: 初期構築フェーズの記録（Discord, CrewAI, PaperTrader立ち上げ）

### 廃棄済み（2026-03-14 整理）
- **39件のAlpha Sweepノイズ**（偽Sharpeデータに基づく自動更新）
- **6件のAIXBT重複Council判定**（プロンプトリーク含む）
- **2件の空Performance記録**（accuracy=0, trades=0）
- **2件のETH/SOL偽Sharpe Council判定**（CRITICAL誤判定）

---

## 🏗️ 現在のシステム仕様（Neo v3.2 — 2026-03-14）

### アーキテクチャ
- **メインレーダー**: `run_trigger.py v2`（30秒間隔、2種トリガー統合）
- **最高意思決定**: `TrinityCouncil v2`（偵察→BT→協議→取引→報告→メモリの7Phase）
- **取引エンジン**: `PaperWallet`（統一ウォレット、$90,000 USDC + VIRTUAL保有）
- **データソース**: CoinGecko OHLC API（30日/180本4h足）+ 1時間キャッシュ
- **報告**: Discord Embed + Moltbook自動投稿

### トリガー条件
1. **ボラティリティ**: VIRTUAL 2%変動 → Council召集
2. **アルファ**: Sharpe 5.0超え（信頼度ガード: min 3取引）→ Council召集
3. **冷却期間**: 30分（両トリガー共通）

### 品質ガード
- **Sharpe信頼度**: 取引3回未満 or inf/nan → Sharpe=0.0
- **BacktestAgent v2**: CSV依存廃止、実データ直結
- **PortfolioManager v2**: PaperWalletに統一（旧paper_balance.json廃止）

### LLMモデル構成
- **Trinity Council（Bull/Bear/Neo）**: gemini-2.0-flash（Google Direct）
- **ScoutCrew**: gemini-2.0-flash（Google Direct）

### 重要ルール
- Moltbook投稿間隔: 最低2.5分（150秒）
- CoinGecko Rate Limit: 6秒間隔
- Python環境: 必ず `./neo-env/bin/python` を使用
- パス: 実行前に `cd workspace`

---

## 📝 記憶書き込みルール
1. **Council判定**: 自動保存（symbol, verdict, accuracyをメタデータに含む）
2. **司令官の教訓**: `source: commander_manual_injection` で永久保持
3. **システム変更**: `category: permanent_record` で保存
4. **Alpha Sweep更新**: ❌ **DBに書き込まない**（Blackboardのみ）
