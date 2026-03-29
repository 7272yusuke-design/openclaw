# 🎓 Graduation Boost — サービス設計書

> **作成日**: 2026/03/29
> **ステータス**: 設計中
> **バージョン**: v1.0

---

## 1. サービス概要

| 項目 | 内容 |
|---|---|
| **offering名** | `graduation_boost` |
| **目的** | Sandboxエージェントのoffering品質テスト＋Graduation要件達成支援 |
| **顧客** | Sandbox状態で止まっているエージェント（のBuyer発注） |
| **単位** | 1ジョブ = 1テスト = 対象offeringへの1回発注＋QAレポート |
| **手数料** | $0.50/回（fixed） |
| **実費** | 対象offeringの価格（requiredFundsで追加請求） |
| **顧客負担合計** | $0.50 + 対象offering実費/回 |

---

## 2. offering.json
```json
{
  "name": "graduation_boost",
  "description": "Test your agent's ACP offerings and earn completed jobs toward Graduation. Neo acts as a Buyer, sends a real job to your specified offering with appropriate test data, and returns a detailed QA report (response quality, speed, schema compliance). 1 job = 1 test. Order 10+ to meet Graduation requirements.",
  "jobFee": 0.5,
  "jobFeeType": "fixed",
  "requiredFunds": true,
  "requirement": {
    "type": "object",
    "properties": {
      "target_wallet": {
        "type": "string",
        "description": "Wallet address of the agent to test (0x...)"
      },
      "target_offering": {
        "type": "string",
        "description": "Name of the offering to test on the target agent"
      },
      "target_offering_price": {
        "type": "number",
        "description": "Price of the target offering in USDC (used to calculate requiredFunds)"
      },
      "test_requirements": {
        "type": "object",
        "default": {},
        "description": "Optional: custom requirements to pass to the target offering. If empty, Neo generates appropriate test data based on the offering's schema."
      }
    },
    "required": ["target_wallet", "target_offering", "target_offering_price"]
  }
}
```

---

## 3. ジョブフロー（1テストの全工程）
```
顧客エージェント                    Neo (Provider)                     対象エージェント (Provider)
     |                                  |                                     |
     |-- job create graduation_boost -->|                                     |
     |   ($0.50 + 対象offering実費)     |                                     |
     |                                  |                                     |
     |                           [Phase: REQUEST]                             |
     |                            1. validateRequirements                     |
     |                               - target_wallet形式チェック              |
     |                               - target_offering存在確認（browse）      |
     |                               - 対象offering価格取得                   |
     |                            2. accept + requestAdditionalFunds          |
     |                               - 実費分をUSDCで追加請求                 |
     |                                  |                                     |
     |                           [Phase: TRANSACTION]                         |
     |                            3. executeJob 開始                          |
     |                               a. 対象offeringスキーマ解析              |
     |                               b. テストデータ生成（or顧客指定を使用）  |
     |                               c. job create → 対象エージェント    ---->|
     |                               d. job status ポーリング（完了待ち）     |
     |                               e. 応答受信                        <----|
     |                               f. QA評価実行                            |
     |                                  - 応答時間                            |
     |                                  - スキーマ整合性                      |
     |                                  - 内容品質スコア                      |
     |                                  - エラー有無                          |
     |                            4. deliverable としてQAレポート返却         |
     |                                  |                                     |
     |<-- QAレポート（deliverable） ----|                                     |
     |                                  |                                     |
     |                           [Phase: COMPLETED]                           |
```

---

## 4. QAレポート（deliverable形式）
```json
{
  "type": "graduation_boost_report",
  "value": {
    "target_wallet": "0x...",
    "target_offering": "offering_name",
    "test_timestamp": "2026-03-29T12:00:00Z",
    "test_requirements_sent": { "symbol": "VIRTUAL" },
    "result": {
      "status": "success | failure | timeout",
      "response_time_ms": 3200,
      "job_id": 12345,
      "phases_completed": ["REQUEST", "NEGOTIATION", "TRANSACTION", "COMPLETED"],
      "deliverable_received": "..."
    },
    "qa_scores": {
      "response_time": { "score": 8, "max": 10, "note": "3.2s — good for analysis type" },
      "schema_compliance": { "score": 10, "max": 10, "note": "All required fields present" },
      "content_quality": { "score": 7, "max": 10, "note": "Data included but lacks source attribution" },
      "error_handling": { "score": "N/A", "note": "No error triggered in this test" }
    },
    "overall_score": 83,
    "graduation_progress": {
      "this_test": "PASS",
      "recommendation": "Offering is functional. Consider adding source URLs to improve content quality."
    }
  }
}
```

---

## 5. ハンドラ実装構成
```
offerings/graduation_boost/
  ├── offering.json          # 上記のoffering定義
  └── handlers.ts            # ハンドラ実装
```

### handlers.ts の責務

| ハンドラ | 処理 |
|---|---|
| `validateRequirements` | target_wallet(0x形式)・target_offering(文字列)チェック |
| `requestAdditionalFunds` | 顧客申告の`target_offering_price`をUSDCで追加請求 |
| `executeJob` | テストデータ生成 → job create → ポーリング → QA評価 → レポート返却 |

---

## 6. 技術的な課題と対策

| 課題 | 対策 |
|---|---|
| **browse でSandbox未卒業エージェントが見えない** | ✅ 解決: 顧客が自己申告（wallet/offering名/価格）。Neoは`job create`で直接発注 |
| **対象offering価格の事前取得** | ✅ 解決: 顧客がrequirementsで`target_offering_price`を申告 |
| **テスト実行のタイムアウト** | 対象エージェントが応答しない場合 → 5分タイムアウト → "timeout" ステータスで報告 |
| **Neoが Buyer として支払う実費の原資** | requiredFundsで顧客から受け取った実費をそのまま使用 |
| **同時並行テストの制御** | 1ジョブ=1テストなので並行問題なし |

---

## 7. 解決済み課題: Sandboxエージェントのofferings取得

### 調査結果（2026/03/29）
- `/acp/agents/<wallet>` → 404（存在しない）
- `/acp/providers/<wallet>` → 404（存在しない）
- `/acp/agents?walletAddress=<wallet>` → 400（queryパラメータ必須）
- browse（`/acp/agents?query=`）→ Butler検索のため卒業済みのみ

### 採用方式: 顧客自己申告
- 顧客がrequirementsで `target_wallet`, `target_offering`, `target_offering_price` を指定
- Neoは `job create <wallet> <offering>` で直接発注（browseを経由しない）
- 価格が不正な場合はジョブ失敗 → QAレポートでエラーとして報告

---

## 8. 次のアクション

1. [x] Sandboxエージェントのofferings取得方法を調査 → 顧客自己申告方式に決定
2. [ ] offering scaffold: `sell init graduation_boost`
3. [ ] handlers.ts 実装
4. [ ] Neo自身のGraduation完了（先決条件）
5. [ ] テスト実行・デバッグ
