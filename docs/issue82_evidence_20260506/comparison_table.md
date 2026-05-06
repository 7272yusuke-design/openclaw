# Issue #82 Additional Evidence (2026-05-06 investigation)

## Decisive: profile-level data inconsistency

| Field | seller (NeoAutonomous, broken) | buyer (neo-test-buyer-v2, working) |
|---|---|---|
| agentId | `019d7b3f-c2d8-7a52-839c-9629f4abb5dc` | `019d76d4-4e69-76c4-99d7-b90c64988af3` |
| wallet | `0x840cff9032a4ce29845e05aed510f0ca4ea16cab` | `0x11ab498cea003b73b66ab48222cb240fe7a9ee82` |
| acpV2AgentId | **41437** (v1 ID reused) | **None** |
| lastActiveAt | **2999-12-31T00:00:00.000Z** (frozen sentinel) | 2026-05-05T04:18:44.015Z |
| updatedAt | 2026-05-06T06:51:10.979Z (just refreshed via PUT, no effect on lastActiveAt) | 2026-05-05T04:18:44.016Z |
| builderCode | (field absent) | `bc_zwlc4yf7` |
| offerings count | 6 (5 missing vs local 11) | 0 |

## What I tried this session

1. `acp agent migrate --agent-id 41437` -> returns "Agent already migrated"
   -> `migrationStatus = COMPLETED` per backend, contradicts the frozen lastActiveAt
2. `acp agent update --description "..."` -> succeeded, `updatedAt` refreshed
   -> but `lastActiveAt` stayed at 2999-12-31, `acpV2AgentId` stayed at 41437

## Hypothesis

Backend has the agent in an inconsistent state where `migrationStatus=COMPLETED` but the v2 indexing/stats pipeline never ran because `acpV2AgentId` is still the legacy v1 number (41437) rather than a fresh v2 ID like other agents (e.g. 2043, 12392, 21257). PUT /agents/:id only updates name/description/image fields and does not re-trigger v2 indexing.

## Request

Could the team please:
1. Re-run the v2 registration/indexing pipeline for agent `019d7b3f-c2d8-7a52-839c-9629f4abb5dc`
2. Issue a fresh acpV2AgentId (or confirm 41437 is acceptable for v2 stats tracking)
3. Apply the same fix to Withdraw flow on ECONOMYOS (`0x75e653970fd3d0c343177fbe7b4c1c85ae0a300a`)

Job #6407 (vp_sentiment_scan, 0.01 USDC) on Base mainnet completed end-to-end including `evaluator job.completed` event, yet none of it was reflected on the seller's profile.

