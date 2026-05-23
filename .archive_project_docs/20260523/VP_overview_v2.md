# 📍 VP関連コードベース 全体像マップ v2

> **作成日**: 2026/05/06
> **作成セッション**: claude.ai リファクタ調査セッション
> **次回更新タイミング**: VP関連の構造に物理的変更があったとき
> **このドキュメントの目的**: 新規セッションのClaude(またはClaude Code)が、VP関連の現状を最短時間で正確に把握できる「地図」

---

## 🎯 このドキュメントを最初に読むべき人

- VP/ACP関連の作業を始めようとしているセッション
- `bridge/acp_client.py` や `agents/trinity_council.py` の変更を検討している人
- VP UI上の表示と実態のズレに困っている人
- Issue #82 のレスを受けて対応する未来のセッション
- Graduation実行計画を再開しようとしているセッション

**先に読むべき関連ドキュメント**:
1. `saikai_tejun_v6_5ak.md` (再開手順 = 設計方針・禁止事項)
2. `docs/GSD計画_v6_5bm_引き継ぎ白書.md` (最新セッション状態)
3. `graduation_history_v2.md` (claude.ai プロジェクトファイル)
4. 本ドキュメント (VP関連の物理構造)

---

## 1. 階層構造マップ

VP関連は **4層** に分かれています:

```
[Layer 1: 物理ストレージ] = ローカルファイルシステム
   ↓
[Layer 2: Runtime] = systemd service が起動するNode.jsプロセス
   ↓
[Layer 3: VP Registry] = Virtuals Protocol側のデータベース(WebUI表示元)
   ↓
[Layer 4: Butler/Marketplace UI] = エンドユーザー/他エージェントが見る世界
```

**重要**: Layer 1〜2は健全だが、Layer 3との同期が壊れている(Issue #82 の主症状)。

**禁止事項**: Issue #82 のレスが来るまで Layer 3 への変更操作(Re-Import等)は禁止。

---

## 2. 物理ファイル構造 (Layer 1)

### 2.1 skills/ 配下の4ディレクトリ

| ディレクトリ | 役割 | 状態 |
|---|---|---|
| `skills/acp-cli-v2/` | v2 seller runtime本体 | 🟢 現役 |
| `skills/acp-cli-v2-buyer/` | buyer用(v2のシンボリックリンク+別config) | 🟢 現役 |
| `skills/virtuals-protocol-acp/` | offerings定義の物理置き場・v1 CLI | 🟢 部分的に現役 |
| `skills/openclaw-acp-v2/` | OpenClaw公式skill packのclone(独立gitリポジトリ) | 🔴 デッドコード(4/10以来未参照) |

### 2.2 各ディレクトリの詳細

#### skills/acp-cli-v2/ (v2 seller runtime)

- 起動: `systemctl start neo-acp-seller-v2.service`
- 実行: `npx tsx src/seller/seller_native_v2.ts`
- 環境変数: `V2_SELLER_DRY_RUN=false` (2026/05/05に解除済)
- activeWallet: `0x840cff9032a4ce29845e05aed510f0ca4ea16cab` (NeoAutonomous v2)
- WorkingDirectory: `/docker/openclaw-taan/data/.openclaw/workspace/skills/acp-cli-v2`
- 重要ファイル:
  - `src/seller/seller_native_v2.ts` — メインエントリポイント
  - `src/seller/offeringsLoader.ts` — offeringsを別ディレクトリから読む
  - `config.json` — Privy walletId、jobRegistry(34件以上)
  - `bin/acp.ts` — CLI(buyer-buyer/が共有)

#### skills/acp-cli-v2-buyer/ (buyer用)

- 物理的にはほぼシンボリックリンク集(`bin/`, `src/`, `node_modules/`, `package.json`, `tsconfig.json` は親ディレクトリ`acp-cli-v2`を共有)
- 独自ファイルは3つだけ:
  - `buyer_test_v2.ts` — 1件発注スクリプト
  - `buyer_batch_v2.ts` — バッチ発注スクリプト
  - `config.json` — activeWallet=`0x11ab498cea003b73b66ab48222cb240fe7a9ee82` (neo-test-buyer-v2)
- 設計思想: 同じコードベースで seller/buyer をconfig.jsonだけ切り替える
- 起動: 手動 `cd skills/acp-cli-v2-buyer && npx tsx buyer_test_v2.ts`(systemd管理外)

#### skills/virtuals-protocol-acp/ (offerings本体)

- パッケージ名: `virtuals-protocol-acp` v0.4.0(GitHub Virtual-Protocol/openclaw-acp)
- 11 offerings の物理ファイルはここ:
  - `src/seller/offerings/{name}/offering.json`
  - `src/seller/offerings/{name}/handlers.ts`
- v2 sellerの`offeringsLoader.ts`がこのディレクトリを `OFFERINGS_ROOT` として参照
- v1 CLIの`bin/acp.ts`もここ(現在は`bridge/acp_client.py` から subprocess で呼ばれる)
- v1 seller(`src/seller/runtime/seller_native.ts`)もここに残っているが、systemdサービス停止済

#### skills/openclaw-acp-v2/ (デッドコード)

- 独立Gitリポジトリ(`.git`あり) — Virtual-Protocol/openclaw-acp のclone
- SKILL.md(25KB) は OpenClaw Agent向けの汎用スキル説明書
- **コードベース内のどこからも参照されていない**(grep結果ゼロ)
- 整理候補だが削除前にgit履歴の精査が必要

---

## 3. Runtime層 (Layer 2)

### 3.1 systemd サービス

| サービス名 | 状態 | 用途 |
|---|---|---|
| `neo-acp-seller-v2.service` | 🟢 active enabled | v2 seller(現役) |
| `neo-acp-seller.service` | 🔴 inactive disabled | v1 seller(停止済) |
| `neo-radar.service` | 🟢 active enabled | メインレーダー(VP関連を含む) |
| `neo-collector.service` | 🟢 active enabled | 市場データ収集 |
| `neo-resource-api.service` | 🟢 active enabled | FastAPI port 8099(リソース公開) |

### 3.2 systemd unit ファイルの注意

`/etc/systemd/system/` に **bakファイルが2つ放置**:

- `neo-acp-seller-v2.service.bak_20260503` (DRY_RUN=true時代)
- `neo-acp-seller-v2.service.bak_before_live_20260505_0131` (DRY_RUN=false解除直前)

両方とも `.archive_deadcode_v65p/` に移動すべき。本番動作には影響しないが、再開手順.mdの「.bak*はsourceに残さない」ルール違反。

### 3.3 v2 seller の起動時ログ

起動毎に以下を出す(直近確認: 2026/05/05 03:43):

```
[v2-seller] [INFO] Loaded 11 offerings: graduation_boost, graduation_complete, 
offering_audit, profile_seo, vp_backtest_on_demand, vp_correlation_risk, 
vp_market_analysis, vp_market_intelligence, vp_sentiment_scan, 
vp_trade_evaluation, vp_whale_alert
```

つまり **Runtime層では11 offerings 全部正常稼働中**。

---

## 4. VP Registry層 (Layer 3) — 最も問題が多い層

### 4.1 現在の登録状態(VP UI Export結果)

VP UI 上で `Export All` した結果は **6 offerings** のみ:

- offering_audit
- vp_market_analysis
- vp_sentiment_scan
- vp_trade_evaluation
- vp_backtest_demand (※ローカルは `vp_backtest_on_demand`、UIは末尾名が異なる)
- profile_seo

**未登録の5 offerings**:

- graduation_boost
- graduation_complete
- vp_correlation_risk
- vp_market_intelligence
- vp_whale_alert

### 4.2 ローカルとVP Registryのスキーマ差

VP UI上の登録内容が、ローカルの最新ファイルより **機能が貧弱な劣化版** になっている。例:

| 項目 | ローカル(現行) | VP Registry(古い) |
|---|---|---|
| vp_market_analysis.symbol enum | VIRTUAL/AIXBT のみ(本来) | VIRTUAL/AIXBT/BTC/ETH(古い拡張) |
| vp_market_analysis.depth プロパティ | ✅ あり | ❌ なし |
| vp_sentiment_scan.include_headlines | ✅ あり | ❌ なし |
| vp_trade_evaluation のプロパティ数 | 7個(高機能) | 5個(劣化) |
| vp_backtest の名前 | `vp_backtest_on_demand` | `vp_backtest_demand` |
| description フィールド | 全offering完備 | 一部欠落(Missing descriptions警告) |

### 4.3 既知の異常 (Issue #82で投稿済)

VP Registry層で発生している3症状:

1. **Stats not yet tracked**: NeoAutonomous v2 のメトリクスが記録されない
2. **Sandbox Butler 検索不可**: Butler が NeoAutonomous を検索結果に出さない
3. **Withdraw が1ヶ月停滞**: $0.001 だけ消費して凍結

GitHub Issue #82 ( https://github.com/Virtual-Protocol/openclaw-acp/issues/82 ) で投稿済、レス待ち。

### 4.4 過去の操作履歴(VP Registry状態が変わった経緯)

- 2026/05/06 前半: claude.ai セッションで `Export All` → 編集版JSONを Import All した(本ドキュメント作成者の前操作)
- このImport操作で、ローカルにある11 offerings のうち6個がVP Registryに反映、残り5個は不明状態に
- Import版JSONは「VP UI Export形式」を前提に作られていたため、ローカルの高機能版より劣化していた

**結論**: VP Registry の現状は「劣化版6 offeringsで上書きされた状態」。Issue #82 とは別問題でユーザー操作起因のズレもある。修復には Issue #82 解決後に Re-Import が必要。

---

## 5. Python統合 (Tier 1: 現役)

### 5.1 Trinity Council 経由のACP参考情報注入

**統合点はたった1箇所**:

```python
# agents/trinity_council.py 21行目
from bridge.acp_client import get_market_intel
```

**bridge/acp_client.py の役割**:

- 信頼エージェント3社から市場情報を取得(参考情報のみ・最終判断はNeo独自)
- 信頼エージェントリスト(`TRUSTED_AGENTS`):
  - Elfa AI (`0x78B1A54C...`) trust=0.7
  - Ask Caesar (`0xc1e1755D...`) trust=0.6
  - PILOT3 (`0x834C4E67...`) trust=0.5
- 結果は5分間キャッシュ
- 内部実装: `npx tsx skills/virtuals-protocol-acp/bin/acp.ts` を subprocess で呼ぶ
- 設計方針: 再開手順.md の「方針X」=「ACP外部エージェントのシグナルは参考情報注入のみ」

### 5.2 VP銘柄発見・宣伝

**orchestration/vp_discovery.py**:

- 週次(月曜JST 04:00) で実行(`run_trigger.py` 813行目)
- CoinGecko VP生態系カテゴリーから新興銘柄を発見
- スクリーニング基準: 時価総額$5M以上、24h出来高$500K以上
- 固定銘柄: VIRTUAL / AIXBT / LUNA(常に含める)

**orchestration/nightly_research.py**:

- `run_graduation_boost_promo()` を土曜実行(`tools/moltbook_tool.py` 経由)
- VP Guide投稿は毎日
- run_trigger.py 958行目に「旧ACP Provider宣伝は廃止 → VP Guide毎日投稿+Graduation Boost土曜投稿」の経緯コメント

### 5.3 Resource API (FastAPI)

**tools/neo_resource_api.py**:

- ポート8099でFastAPI公開
- ACPの「Resources」機能(v2の新概念)に相当
- 他エージェントが Job不要で読み取れるエンドポイント

---

## 6. ウォレット構成

### 6.1 4つのエージェントウォレット (acp-cli-v2/config.json)

| アドレス | 役割 | activeWallet設定 | 残高(USDC) |
|---|---|---|---|
| `0x840cff9032a4ce29845e05aed510f0ca4ea16cab` | NeoAutonomous v2 (seller本体) | seller側のactive | $2.268 |
| `0x11ab498cea003b73b66ab48222cb240fe7a9ee82` | neo-test-buyer-v2 | buyer側のactive | $1.853 |
| `0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a` | ECONOMYOS(旧テストエージェント) | なし | $0.099 (Withdraw失敗で凍結) |
| `0x131d3ff8250b00da4753b06317d826ffefde5912` | (作成途中の空ウォレット) | なし | $0 (publicKey空・署名不可) |

### 6.2 VP login wallet (config.json外)

| アドレス | 役割 | 残高 |
|---|---|---|
| `0x8824ADF8e...ABFFC8f3870` | ブラウザログイン用(MetaMask等) | $4.000 |

### 6.3 認証構造の特徴

- 全ウォレットは Privy 管理(P256キー + walletId)
- `privateKey` フィールドはconfig.jsonに存在しない = サーバー側に秘密鍵なし
- 通常の web3 スクリプトでは送金不可能
- ガス代は Virtuals 側がスポンサー(ETH残高ゼロでもジョブ動作)

### 6.4 Withdraw禁止事項 (白書v6.5bm より)

- 残り2ウォレット(buyer $1.85 / seller $2.27)の Withdraw 試行は **絶対禁止**
- 理由: ECONOMYOSの$0.10が1ヶ月凍結状態(Withdrawで$0.001消費後・送金未完了)
- Issue #82 のVP側調査結果待ち

---

## 7. オファリング 11個の完全リスト

| ローカル名 | 登録名 | 価格(USDC) | カテゴリ |
|---|---|---|---|
| graduation_boost | graduation_boost | $0.10 | Graduation支援 |
| graduation_complete | graduation_complete | $0.50 | Graduation支援(フルパッケージ) |
| offering_audit | offering_audit | $0.30 | 品質監査 |
| profile_seo | profile_seo | $0.30 | SEO最適化 |
| vp_backtest_on_demand | vp_backtest_on_demand | $1.00 | 取引分析 |
| vp_correlation_risk | vp_correlation_risk | $0.30 | リスク分析 |
| vp_market_analysis | vp_market_analysis | $0.50 | 市場分析 |
| vp_market_intelligence | vp_market_intelligence | $0.50 | 市場情報 |
| vp_sentiment_scan | vp_sentiment_scan | **$0.01** | センチメント(テスト価格) |
| vp_trade_evaluation | vp_trade_evaluation | $0.50 | 取引評価 |
| vp_whale_alert | vp_whale_alert | $0.30 | クジラ監視 |

合計: **11個 / $4.51**

`vp_sentiment_scan` の $0.01 はJob #6333完走時のテスト価格のまま。本番化時は要検討。

---

## 8. デッドコード一覧 (整理候補)

| 場所 | 種類 | 整理判定 |
|---|---|---|
| `skills/openclaw-acp-v2/` | OpenClaw公式skill packのclone | 削除可(参照ゼロ) |
| `agents/acp_executor_agent.py` | CrewAI Agent定義 | archive可(参照ゼロ) |
| `skills/virtuals-protocol-acp/src/seller/runtime/seller_native.ts` | v1 seller本体 | archive可(systemd停止済) |
| `/etc/systemd/system/neo-acp-seller.service` | v1 sellerのunit | archive可(disabled済) |
| `/etc/systemd/system/neo-acp-seller-v2.service.bak_20260503` | DRY_RUN=true時代のbak | `.archive_deadcode_v65p/` 移動 |
| `/etc/systemd/system/neo-acp-seller-v2.service.bak_before_live_20260505_0131` | DRY_RUN=true時代の最終bak | `.archive_deadcode_v65p/` 移動 |
| `docs/graduation_history.md` | 旧版(2026/04/01) | archive可(v2が claude.ai に存在) |

---

## 9. VP統合の歴史 (主要マイルストーン)

```
v6.5e   ACP offering最初の登録 + Moltbook pivot
v6.5l   6 offerings達成
v6.5o   Graduation Boost service suite(3 offerings追加)
v6.5r   graduation_complete 追加・Discord通知実装
v6.5t   Buyer戦略策定・Graduation手順確定
v6.5u   価格改定 graduation_boost $0.50→$0.10
v6.5v   Graduation挑戦→OpenClaw制限判明
v6.5w   Native ACP SDK migration(OpenClaw CLI廃止)
v6.5x   Evaluator検証・skip-eval COMPLETED 成功
v6.5ac  vp_market_intelligence offering 追加
v6.5at  Council fix + ACP v2 migration + 10 jobs completed
v6.5az  v2 seller設計確定セッション
v6.5ba  v2 seller runtime実装完了(seller_native_v2.ts)
v6.5bg  Graduation問題方針再検証 + Phase 0/1完了
v6.5bh  Phase 2 着手 + setBudget実装欠落の発見・修正
v6.5bi  Phase 2.2 完了 - 1件本番ジョブ完走 (Job #6333)
v6.5bk  ACP v2 graduation deep-dive (lastActiveAt issue ongoing)
v6.5bl  ACP graduation 真因切り分け + 公式ドキュメント精読
v6.5bm  Sandbox Butler検証 + Withdraw異常検出 + GitHub Issue #82投稿 ★最新
```

---

## 10. 既知の問題と現状

### 10.1 Issue #82 (VP側調査待ち)

- URL: https://github.com/Virtual-Protocol/openclaw-acp/issues/82
- 投稿者: 7272yusuke-design
- ステータス: Open
- 含まれる症状: Stats未追跡 / Butler検索不可 / Withdraw停滞
- 戦略: レス来るまでACP関連の追加投資・追加ジョブ発注禁止

### 10.2 VP Registryの劣化版上書き (本ドキュメント作成者の前操作起因)

- claude.ai セッションでJSON編集 → Import All した結果、VP Registry が劣化版6 offeringsで上書きされた状態
- ローカルファイル(11個・高機能版)とは大きくズレている
- 修復: Issue #82解決後にローカル版を Re-Import する必要

### 10.3 Builder Code 設定済 (seller側未反映)

- VP UI上で `bc_agxzezgu` が登録済(2026/05/06)
- seller_native_v2.ts への反映は未実施(seller再起動リスクで延期)
- 今後Base chain上の取引が「Neoのアプリから出た」と帰属されるが、現時点では未反映のため帰属なし

---

## 11. このドキュメントの更新ルール

- **更新タイミング**: VP関連の構造に物理的変更があったとき
- **更新者**: その変更を行ったセッション
- **更新例**:
  - 新規offering追加 → 第7章を更新
  - サービス停止/起動 → 第3章を更新
  - 新規ウォレット追加 → 第6章を更新
  - Issue #82のレス対応 → 第10章を更新

更新時は冒頭の「作成日」を「最終更新日」に変更し、変更概要を以下の改訂履歴に追記する。

---

## 12. 改訂履歴

| 日付 | バージョン | 変更概要 | 担当 |
|---|---|---|---|
| 2026/05/06 | v2.0 | 初版作成(claude.aiリファクタ調査セッション) | claude.ai |
