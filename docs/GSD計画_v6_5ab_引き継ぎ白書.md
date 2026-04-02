# 📐 GSD計画 v6.5ab 引き継ぎ白書

> **更新日時**: 2026/04/02 16:00 JST
> **セッション**: v6.5ab（Discord報告ブラッシュアップ・ARCHITECTURE更新セッション）
> **自己採点**: 88/100（Discord全6種更新、ARCHITECTURE反映、勝率分析完了）

---

## 🔴 今すぐ知るべきこと

| 項目 | 値 |
|---|---|
| 勝率 | **57.1%**（28ペア: 16勝12敗）⚠️ 60%割れ継続（AIXBT 50%が主因） |
| Tier0勝率 | 0%（BTC/ETH取引開始待ち — 初回BTC Council完了→WAIT判断） |
| USDC | $87,979.91 |
| Holdings | なし |
| サービス | 全4サービス稼働中 |
| CFO L4 | ドローダウンブロック発動中（HWM $88,494） |
| Council | 2hローテーション: BTC → VIRTUAL → ETH（3銘柄・AIXBTはTier2降格） |

---

## ✅ 本セッション完了タスク

### Task: Discord報告ブラッシュアップ（全6種）
| 報告種別 | 修正内容 |
|---|---|
| Council Minutes | Tierバッジ追加、`_fmt_price`でBTC/VP自動切替、BUY時にexit_profile詳細表示 |
| Trade Alert (TP/SL) | `_fmt_price`対応、exit_profileフィールド追加、balance_afterカンマ区切り |
| Performance Dashboard | Tier0/Tier1勝率個別表示、旧TP/SL固定値→戦略別出口プロファイル一覧に差替 |
| Heartbeat | Tier別勝率・CFOドローダウン状態+HWM・次ローテーション銘柄+残り時間追加 |
| Nightly Batch | Tier別勝率行追加 |
| send_log各種 | 変更なし（汎用のため問題なし） |

**新規追加**: `_fmt_price(price, symbol)` — BTC/ETH=$65,432.10 / VP=$0.001234 自動切替

### Task: ARCHITECTURE.md更新（v6.5p → v6.5aa）
- Tier0/2hローテーション/戦略別出口/Tier別勝率/Discord報告/Graduation状況を反映

### Task: Heartbeat CFOバグ修正
- `current_level()`（存在しないメソッド）→ `check_drawdown()` に修正

### Task: 勝率低下原因分析
- **AIXBT 50%（18件中9勝）が全体を引き下げ**: 3/26以降ほぼ全敗（直近10件中9敗）
- **原因**: $0.0265→$0.0224の-15%下落トレンドへの繰り返しエントリー
- **対処**: ローテーション導入でAIXBT比率が50%→25%に自然低下。追加対処不要と判断
- **VIRTUAL 70%（10件中7勝）は健全**

---

## ⏭️ 次セッションの作業

### 短期（次回）
1. **2hローテーション観測**: BTC→VIRTUAL→ETH→AIXBT が正しく発火するか確認（数サイクル分のログ検証）
2. **BTC/ETH初BUY発生の確認**: Councilが実際にBUY判断を出したとき、strategy_tagが正しく保存されるか
3. **CFR急変時のポジション調整（Step 2設計）**: CFRレジーム急変時にexit_profileの動的上書き機能
4. **Graduation Discord返答確認**: NeoAutonomous Graduateボタン問題のDevRel回答待ち

### 中期
5. **Phase 4: 実取引エンジン（Binance Spot API）** — `tools/cex_executor.py` 新設
6. **Phase 5: 少額実取引** — $50テスト → 段階的引き上げ
7. **Graduation Video Demo準備** — ターミナル+ACP Visualizerの録画
8. **OpenClawアップデート計画** — Graduation完了後に実施（下記メモ参照）

---

## 🔒 OpenClawアップデートメモ（Graduation後に対応）

| 項目 | 値 |
|---|---|
| 現在のバージョン | **2026.2.19**（ビルド日: 2026-02-20） |
| 最新安定版 | **2026.3.31**（6週間・13リリース分の遅れ） |
| Dockerイメージ | `ghcr.io/hostinger/hvps-openclaw:latest`（Hostinger管理、自動更新なし） |
| config.json記載 | `lastTouchedVersion: 2026.2.12` |

### セキュリティ評価（2026/04/02時点）
- **CVE-2026-27646（ACP sandbox escape, 修正: 3.7）**: 理論上該当するがNeoはseller_native.tsで直接動作しておりOpenClaw ACPサンドボックス非経由。実質リスク低
- **CVE-2026-32914（/config不正アクセス, 修正: 3.12）**: 外部公開なし。リスク低
- その他6件のCVE: いずれもNeoの攻撃面外（Gateway UI/ブラウザ/サブエージェント未使用）
- **結論: 緊急対応不要。Graduation完了後にアップデート推奨**

### アップデート時の注意点
- v2026.3.2〜3.22で**13件のbreaking changes**あり
- コミュニティでも「アプデで壊れた」報告多数（ツール無効化、config形式変更等）
- `openclaw doctor --fix`で大半は修復可能とされる
- **手順**: バックアップ → docker-compose.ymlでバージョン指定 → テスト → 本番反映
- **代替案**: OpenClaw本体は据え置きでACP CLI（`skills/virtuals-protocol-acp`）のみ`npm update`

---

## 📊 変更ファイル一覧

| ファイル | 変更内容 |
|---|---|
| `tools/discord_reporter.py` | `_fmt_price()`追加、send_performance_dashboardにTier別勝率・戦略別出口、send_council_minutesにTier/exit_profile/symbol、send_trade_alertにexit_profile引数、全フッター統一 |
| `run_trigger.py` | Heartbeatに勝率/CFO/次ローテーション追加、Nightly BatchにTier別勝率追加、TP/SL報告にexit_profile/価格フォーマット追加、CFO current_level()→check_drawdown()修正 |
| `agents/trinity_council.py` | discussion_dataにsymbol/tier/exit_profile追加 |
| `ARCHITECTURE.md` | v6.5p→v6.5aa全更新 |

---

## 🔧 システム構成（変更点のみ）
```
[Discord報告] — 全6種ブラッシュアップ
  _fmt_price(): BTC/ETH=カンマ区切り, VP銘柄=小数点
  Council Minutes: Tierバッジ + exit_profile
  Trade Alert: exit_profile + 価格フォーマット
  Dashboard: Tier0/Tier1個別勝率 + 戦略別出口
  Heartbeat: 勝率/CFO DD/次ローテーション
  Nightly: Tier別勝率行

[Heartbeat] — CFOステータス修正
  旧: CostGuard.current_level()（存在しないメソッド）
  新: CostGuard.check_drawdown() → DD状態+HWM表示
```

---

## 📚 出口プロファイル一覧（config.py）

| カテゴリ | 戦略 | SL | Trail開始 | Trail幅 | Hard TP | 時間上限 |
|---|---|---|---|---|---|---|
| mean_reversion | rsi_bounce, bb_reversal, mean_reversion | -5% | +5% | -2.5% | +14% | 96h |
| trend_follow | macd_cross, ema_trend, momentum_breakout, vp_momentum, alpha_strategy | -8% | +10% | -4% | +30% | 2週間 |
| evolved | gplearn_evolved | -8% | +10% | -4% | +30% | 2週間 |

---

## 📈 勝率分析サマリー

| 銘柄 | 勝率 | 件数 | 備考 |
|---|---|---|---|
| VIRTUAL | **70%** | 10件 | 健全 |
| AIXBT | **50%** | 18件 | 3/26以降連敗。ローテーション25%化で自然治癒見込み |
| BTC | N/A | 0件 | Tier0新規。初回WAIT判断済み |
| ETH | N/A | 0件 | Tier0新規。未発火 |
| **総合** | **57.1%** | 28件 | 目標60%に対し-2.9pt |
