# 📐 D.3 Binance 本番取引移行計画書

> **作成日**: 2026/04/06
> **ステータス**: 計画段階
> **現行**: Paper Trading（PaperWallet）
> **移行先**: Binance CEX（スポット取引）

---

## 1. 移行条件（D2準拠・変更不可）

| 条件 | 現在の状態 | 必要条件 | 判定 |
|---|---|---|---|
| Paper勝率 | 61.5%（26ペア決済） | **60%以上** | ✅ 達成 |
| 継続期間 | 2026/03/14〜（23日経過） | **3ヶ月継続** | ⏳ 最短 06/14 |
| 取引回数 | 73回（26ペア決済） | **100回完了** | ⏳ 進行中 |
| 学習モード | ON | **OFF（100回後）** | ⏳ |
| L4 DD | 4.99%（ギリギリ） | **安定運用** | ⚠️ 要改善 |

→ **最短移行可能日: 2026/06/14**

---

## 2. なぜBinance（CEX）か

| 比較項目 | DEX（Aerodrome / D2案） | CEX（Binance） |
|---|---|---|
| ガス代 | 毎回発生（Base chain） | なし |
| スリッページ | 流動性に依存（小型トークン注意） | 板が厚く安定 |
| 対応銘柄 | Base chainトークンのみ | BTC/ETH/VIRTUAL等幅広い |
| 秘密鍵管理 | 自前ウォレット必須 | APIキー管理のみ |
| 約定速度 | ブロック確認待ち | 即時 |
| カウンターパーティリスク | なし（オンチェーン） | **あり（取引所リスク）** |
| KYC | 不要 | **必要** |

---

## 3. ユーザー側の事前準備（Claude不要・自分でやるもの）

### 3.1 Binanceアカウント準備
- [ ] Binanceアカウント作成（持っていなければ）
- [ ] **KYC本人確認を完了**する（API取引に必要）
- [ ] 2FA（二段階認証）を有効化

### 3.2 APIキー発行
- [ ] Binance > API Management > APIキー作成
- [ ] 権限設定:
  - ✅ **Enable Spot Trading**（スポット取引）
  - ✅ **Enable Reading**（残高読み取り）
  - ❌ Withdrawals は**無効**にする（出金不可＝安全策）
  - ❌ Futures は**無効**（レバレッジ取引しない）
- [ ] **IP制限を設定**（サーバーのグローバルIPのみ許可）
- [ ] API Key と Secret Key を安全に保管

### 3.3 資金入金
- [ ] Binanceに**USDT or USDC**を入金
- [ ] 初期テスト資金: **$100〜$500**（少額から開始）
- [ ] 本格運用資金: 別途判断（Paper実績を見て決定）

### 3.4 サーバーIP確認
```bash
curl -s ifconfig.me
# → このIPをBinance API制限に登録
```

---

## 4. 開発側の実装ステップ

### Phase A: インフラ準備（移行1ヶ月前）

| # | タスク | 担当 | 備考 |
|---|---|---|---|
| A1 | `.env` に Binance API キー追加 | ユーザー | `BINANCE_API_KEY` / `BINANCE_API_SECRET` |
| A2 | `python-binance` ライブラリインストール | Claude | `pip install python-binance` |
| A3 | API接続テストスクリプト作成 | Claude | 残高取得・価格取得の動作確認 |
| A4 | `core/config.py` に本番モード設定追加 | Claude | `LIVE_MODE` / `EXCHANGE` / `MAX_TRADE_USD` |

### Phase B: トレード実行エンジン開発（移行3週間前）

| # | タスク | 担当 | 備考 |
|---|---|---|---|
| B1 | `tools/binance_executor.py` 新規作成 | Claude | 注文送信・約定確認・残高同期 |
| B2 | 注文タイプ実装 | Claude | 成行（MARKET）メイン、指値（LIMIT）オプション |
| B3 | PaperWallet互換インターフェース | Claude | 既存コードの呼び出し元を変えずに切替可能に |
| B4 | `DRY_RUN` モード実装 | Claude | 注文生成のみ・送信しない |
| B5 | 残高同期ロジック | Claude | Binance残高 ↔ 内部状態の整合性維持 |

### Phase C: 安全装置実装（移行2週間前）

| # | タスク | 担当 | 備考 |
|---|---|---|---|
| C1 | 最大取引額ガード | Claude | `MAX_TRADE_USD=100`（初期） |
| C2 | 日次取引上限 | Claude | CostGuardと連動 |
| C3 | 緊急停止スイッチ | Claude | `LIVE_MODE=False` → 即Paper復帰 |
| C4 | 注文失敗リトライ/ロールバック | Claude | ネットワーク障害時の安全処理 |
| C5 | Paper/Live並行稼働モード | Claude | 比較検証用 |

### Phase D: テスト（移行1週間前）

| # | タスク | 担当 | 備考 |
|---|---|---|---|
| D1 | Binance Testnet でのE2Eテスト | Claude | testnet.binance.visionを使用 |
| D2 | DRY_RUN 10回エラーなし確認 | 両方 | 本番APIで注文生成のみ |
| D3 | 少額実取引テスト（$10〜$20） | 両方 | 1〜3回の実取引で動作確認 |
| D4 | Paper/Live残高比較 | 両方 | 同一判断で結果が一致するか |

### Phase E: 本番移行（段階的）

| ステップ | MAX_TRADE_USD | 期間 | 条件 |
|---|---|---|---|
| E1 少額テスト | $50 | 1週間 | 問題なし確認 |
| E2 小規模運用 | $200 | 2週間 | 勝率維持確認 |
| E3 通常運用 | $500 | 継続 | Paper実績と乖離なし |
| E4 拡大（任意） | $1,000+ | — | 十分な実績後 |

---

## 5. アーキテクチャ変更

```
現在（Paper Trading）:
  TrinityCouncil → Phase 5 → PaperWallet.execute_trade()
                                └ data/paper_wallet.json 更新のみ

移行後（Binance Live）:
  TrinityCouncil → Phase 5 → TradeRouter.execute_trade()
                                ├ LIVE_MODE=True  → BinanceExecutor.execute_trade()
                                │                    ├ Binance API で注文送信
                                │                    ├ 約定確認・残高同期
                                │                    └ 取引ログ記録
                                ├ LIVE_MODE=False → PaperWallet.execute_trade()（既存）
                                └ DRY_RUN=True    → 注文生成のみ・ログ出力
```

### 5.1 新規作成ファイル

| ファイル | 役割 |
|---|---|
| `tools/binance_executor.py` | Binance APIへの注文送信・約定管理 |
| `tools/trade_router.py` | LIVE_MODE に応じて Paper/Binance を切替 |

### 5.2 既存ファイルの修正

| ファイル | 変更内容 |
|---|---|
| `agents/trinity_council.py` | Phase 5: TradeRouter経由に変更 |
| `core/config.py` | `LIVE_MODE` / `EXCHANGE` / `MAX_TRADE_USD` / `DRY_RUN` 追加 |
| `.env` | `BINANCE_API_KEY` / `BINANCE_API_SECRET` 追加 |
| `tools/paper_wallet.py` | Binance残高同期メソッド追加（オプション） |

---

## 6. 安全装置一覧

| 装置 | 仕様 | 備考 |
|---|---|---|
| 最大取引額 | $100/回（初期）→ 段階引き上げ | `MAX_TRADE_USD` |
| 日次上限 | $1,000（CostGuard L1連動） | 既存の仕組みを流用 |
| L4 DD上限 | HWMから-5%で全BUYブロック | 既存（変更なし） |
| API出金無効 | Binance側でWithdrawals OFF | **ユーザー設定** |
| IP制限 | サーバーIPのみ許可 | **ユーザー設定** |
| 緊急停止 | `LIVE_MODE=False` → 即Paper復帰 | 未約定注文は自動キャンセル |
| DRY_RUN | 注文JSONを生成・ログ出力のみ | 送信しない |
| Paper並行 | Live中もPaperに同じ判断を記録 | 比較検証用 |
| 注文タイムアウト | 30秒以内に約定しなければキャンセル | ネットワーク障害対策 |

---

## 7. .env に追加する変数

```bash
# === Binance本番取引 ===
LIVE_MODE=False              # True で本番、False で Paper
DRY_RUN=True                 # True で注文生成のみ
EXCHANGE=binance             # 取引所指定
BINANCE_API_KEY=xxxxx        # ユーザーが設定
BINANCE_API_SECRET=xxxxx     # ユーザーが設定
MAX_TRADE_USD=100            # 1回の最大取引額
DAILY_TRADE_LIMIT_USD=1000   # 日次取引上限
```

---

## 8. Binance対応銘柄マッピング

| Neo内部シンボル | Binanceペア | 備考 |
|---|---|---|
| BTC | BTC/USDT | 流動性最大 |
| ETH | ETH/USDT | 流動性最大 |
| VIRTUAL | VIRTUAL/USDT | **Binance上場を確認要** |

> ⚠️ VIRTUALがBinanceに上場していない場合、DEX併用またはBybit等の代替を検討

---

## 9. リスクと対策

| リスク | 対策 |
|---|---|
| APIキー漏洩 | `.env`保管・git除外・IP制限・出金権限OFF |
| 取引所ダウン | 注文タイムアウト + 自動Paper復帰 |
| 約定スリッページ | 成行注文は小口に分割、板の薄い時間帯を回避 |
| Paper/Liveの乖離 | 並行運用で差異を監視・大きな乖離時はアラート |
| 想定外の大量注文 | MAX_TRADE_USD + 日次上限の二重ガード |
| 取引所カウンターパーティリスク | 必要以上の資金を置かない（運用資金のみ） |
| レートリミット | Binance API制限（1200 req/min）に余裕を持った設計 |

---

## 10. 移行判断チェックリスト

全項目 ✅ で移行開始:

### ユーザー側
- [ ] Binanceアカウント作成・KYC完了
- [ ] APIキー発行（Spot Trading + Reading のみ）
- [ ] IP制限設定済み
- [ ] テスト資金入金（$100以上）
- [ ] `.env` にAPIキー設定済み

### システム側
- [ ] Paper勝率60%以上を3ヶ月維持（〜2026/06/14）
- [ ] 学習モード100回完了
- [ ] `binance_executor.py` 実装完了
- [ ] `trade_router.py` 実装完了
- [ ] Testnet E2Eテスト合格
- [ ] DRY_RUN 10回エラーなし
- [ ] 少額実取引テスト（$10〜$20）成功
- [ ] CostGuardとの連動確認
- [ ] 緊急停止テスト（LIVE_MODE=False → Paper復帰）
- [ ] Paper/Live並行稼働テスト

---

## 11. タイムライン目安

```
2026/04 〜 05    Paper運用継続（勝率・取引回数の条件達成を目指す）
2026/05 前半     ユーザー: Binanceアカウント・APIキー準備
2026/05 後半     Phase A〜C: 実装・安全装置構築
2026/06 前半     Phase D: テスト（Testnet → DRY_RUN → 少額実取引）
2026/06/14〜     Phase E: 条件達成後、段階的に本番移行
```

---

## 12. D2（DEX案）との関係

D2（Aerodrome DEX移行設計書）は凍結とする。将来VIRTUALのDEX直接取引が必要になった場合に再検討。Binance CEXで対応できない銘柄が出た場合のみDEX併用を検討する。
