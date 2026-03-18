# MEMORY.md — Neo Long-Term Memory Index
> **最終更新**: 2026-03-18（ChromaDB整理 + LUNA DEXバグ修正）
> **記憶DB**: ChromaDB (`vault/chroma_db/`) — コレクション: `neo_memories`（66件）
> **書き込みルール**: trinity_council.pyのみがChromaDBに書き込む

---

## 📌 記憶の分類と保持方針

### Tier 1: 永久保持（教訓・原則）3件
| 内容 | タグ |
|---|---|
| Discordスパムフィルタ教訓（シャドウブロック発生条件） | Discord,spam,shadow_block |
| クジラ「Accumulating」サインのダマシ対策 | whale,fake_signal,VIRTUAL,AIXBT |
| Moltbook投稿ルール（最低2.5分間隔・スパムキーワード禁止） | Moltbook,rate_limit,spam |

### Tier 2: 重要参照（システム運用ルール）4件
| 内容 |
|---|
| Git 100MB制限: neo-env/バイナリは.gitignore必須 |
| システム整合性: .envパースエラー対策・環境変数は常にクリーンに |
| LUNA利確成功記録（正常データのみ保持） |

### Tier 3: 通常記録 59件
| 種別 | 件数 | 内容 |
|---|---|---|
| 日次ログ | 7件 | 2026-02-17〜02-28の初期構築フェーズ記録 |
| BUY取引記録 | 約32件 | VIRTUAL/LUNA/AIXBT等のBUY判定 |
| WAIT取引記録 | 20件 | 直近20件のみ保持（古いものは削除済み） |

---

## 🧠 自己改善フィードバックループ（v4.3〜）
```
取引実行時（Phase 8）
  → 保存: 価格・action・sentiment・score・判断理由・bt_confidence
  → メタデータ: symbol / action / category=trade_record / tier=3

利確発動時（Phase 1-TP）
  → 保存: エントリー→利確価格・損益% / 教訓テキスト
  → メタデータ: category=trade_result / result=win / tier=2

損切発動時（Phase 1-SL）
  → 保存: エントリー→損切価格・損益% / 教訓テキスト
  → メタデータ: category=trade_result / result=loss / tier=2

次回Council召集時（Phase 1d）
  → recall: 教訓・銘柄別取引結果・利確/損切パターン（最大6件）
  → Councilプロンプトに注入して判断精度を向上
```

---

## 🏗️ 現在のシステム仕様（Neo v4.3 — 2026-03-18）

### アーキテクチャ
- **メインレーダー**: `run_trigger.py`（30秒間隔）
- **最高意思決定**: `TrinityCouncil v2`（8Phase）
- **取引エンジン**: `PaperWallet`（ポジション管理付き・利確+20%/損切-10%自動執行）
- **学習モード**: ON（Sharpe 0.5以上でCouncil召集・100回達成まで）
- **データソース**: CoinGecko OHLC API + DexScreenerオンチェーン

### 価格取得ルール（2026-03-18修正）
- **VIRTUAL/AIXBT**: GeckoTerminal（Base chain DEX）→ フォールバック: CoinGecko
- **LUNA**: CoinGeckoのみ（Solanaチェーントークン。Base chain DEX対象外）
- **ETH/SOL/BNB**: CoinGeckoのみ

### トリガー条件
1. **ボラティリティ**: VIRTUAL 2%変動 → Council召集
2. **アルファ**: Sharpe 0.5超え（学習モード中）→ Council召集
3. **利確**: 保有ポジション +20%到達 → 即SELL
4. **損切**: 保有ポジション -10%到達 → 即SELL
5. **冷却期間**: 30分（両トリガー共通）

### LLMモデル構成
- **Trinity Council（Bull/Bear/Neo）**: gemini-2.0-flash（Google Direct）
- **ScoutCrew / SentimentCrew**: gemini-2.0-flash（Google Direct）
- **Moltbook生成**: Gemini（Google Direct）

---

## 📝 記憶書き込みルール（v4.3確定版）

### ✅ 書き込む
1. **Council判定結果**: symbol / action / sentiment / bt_confidence / 判断理由
2. **利確成功教訓**: エントリー→利確価格・損益% / tier=2
3. **損切実行教訓**: エントリー→損切価格・損益% / tier=2
4. **司令官の手動注入**: `tools/inject_knowledge.py` で永久保持
5. **VP新興銘柄発見**: `orchestration/vp_discovery.py` から自動保存

### ❌ 書き込まない
- Alpha Sweep自動更新（Blackboardのみ）
- performance_summary更新（Blackboardのみ）
- execution_history更新（Blackboardのみ）
- Blackboard経由の自動書き込み（`core/blackboard.py`から書き込み禁止）

---

## 🗑️ 廃棄済み記憶（整理履歴）
- **2026-03-18**: 72件削除（異常利確3件 + accuracy=0.0%の15件 + 古いWAIT54件）
- **2026-03-16**: 207件削除（WAITログ・performance_summary自動更新）
- **2026-03-14**: 42件削除（Alpha Sweepノイズ・重複・プロンプトリーク）

---

## 🐛 修正済みバグ（再発防止）
- **2026-03-18**: LUNAの価格取得バグ修正
  - 原因: LUNA(_GECKO_PAIRS)がBase chain DEXアドレスを参照 → $0.007のLUNAが$0.15のトークン価格で利確判定
  - 修正: `_GECKO_PAIRS`からLUNA削除。`trinity_council.py`もCoinGecko経由に統一
