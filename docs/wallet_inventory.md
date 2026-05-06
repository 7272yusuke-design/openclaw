# Neo VP Wallet Inventory

> 最終更新: 2026/05/06
> 目的: VP関連ウォレット4個 + ログイン用ウォレット1個の正体・残高・状態を1箇所にまとめる

---

## エージェントウォレット (skills/acp-cli-v2/config.json で管理)

| アドレス | 名前 | 役割 | activeWallet | USDC残高 | ETH | 状態 |
|---|---|---|---|---|---|---|
| 0x840cff9032a4ce29845e05aed510f0ca4ea16cab | NeoAutonomous v2 | seller本体 | acp-cli-v2 側 active | $2.268 | 0 | 現役 |
| 0x11ab498cea003b73b66ab48222cb240fe7a9ee82 | neo-test-buyer-v2 | テストバイヤー | acp-cli-v2-buyer 側 active | $1.853 | 0 | 現役 |
| 0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a | ECONOMYOS | 旧テストエージェント | なし | $0.099 | 0 | 凍結 (Withdraw失敗) |
| 0x131d3ff8250b00da4753b06317d826ffefde5912 | (空ウォレット) | 作成途中 | なし | $0.000 | 0 | publicKey空・署名不可 |

## ブラウザログイン用 (config.json外)

| アドレス | 役割 | USDC残高 |
|---|---|---|
| 0x8824ADF8e...ABFFC8f3870 | VP login wallet (MetaMask等) | $4.000 |

## Privy walletId 一覧

```
0x840cff90... -> fjw429slut1eygk4gipj7y6d
0x11ab498c... -> ebwhtj033sjo8cfx17fdlm86
0x75e65397... -> q6819z8fmd2ios2l6nnrf505
0x131d3ff8... -> (空)
```

## Agent ID 一覧

```
0x840cff90... -> 019d7b3f-c2d8-7a52-839c-9629f4abb5dc (NeoAutonomous v2)
0x11ab498c... -> 019d76d4-4e69-76c4-99d7-b90c64988af3 (neo-test-buyer-v2)
0x75e65397... -> 019d7659-6dd1-7067-a5ff-d74f567a3961 (ECONOMYOS)
0x131d3ff8... -> 019d7bb4-d669-7809-a171-e6996c632eea (空ウォレット)
```

## Builder Code

- コード: bc_agxzezgu (VP UI登録: 2026/05/06)
- 反映先: skills/acp-cli-v2/src/lib/agentFactory.ts (2026/05/06 v6.5bnリファクタで実装)
- 適用範囲: createProviderFromConfig 経由の全provider (seller + buyer の両方)
- 動作: SDK内蔵 PrivyAlchemyEvmProviderAdapter が Attribution.toDataSuffix で全 sendTransaction に自動付加
- 検証: https://builder-code-checker.vercel.app/ で新規発生したジョブの tx を確認可能

## 重要事項

### 認証構造
- 全ウォレットは Privy 管理 (P256キー + walletId)
- privateKey フィールドはconfig.jsonに存在しない = サーバー側に秘密鍵なし
- 通常のweb3スクリプトでは送金不可能
- ガス代は Virtuals 側がスポンサー

### Withdraw禁止事項 (白書v6.5bm)
- 残2ウォレット (buyer / seller) のWithdraw試行は絶対禁止
- 理由: ECONOMYOSの$0.10が1ヶ月凍結状態 (Withdrawで$0.001消費後・送金未完了)
- Issue #82 のVP側調査結果待ち

### activeWallet 切替について
- skills/acp-cli-v2/config.json の activeWallet が seller側を決定
- skills/acp-cli-v2-buyer/config.json の activeWallet が buyer側を決定
- 切替は config.json を直接編集 + サービス再起動

## 残高更新履歴

| 日付 | アドレス | 変動 | 理由 |
|---|---|---|---|
| 2026/05/05 | 全ウォレット | スナップショット | 白書v6.5bm |

---

## 改訂履歴

| 日付 | 変更内容 | 担当 |
|---|---|---|
| 2026/05/06 | 初版作成 (v6.5bnリファクタセッション、Builder Code反映と同時) | claude.ai+VPS |
