# GSD計画 v6.5be 引き継ぎ白書

- 更新日時: 2026/04/22 JST
- セッション: v6.5be（Phase 4c — ルールベースverdict決定権の確立）
- 自己採点: 効果観察前のため採点保留

---

## 🎯 本セッションの主要成果

### 🥇 Phase 4c新設 — 取引停止の真の根本原因を解消
- **問題**: Phase 4bはconfidenceのみ上書きし、verdict自体はLLMが独占
  - 直近10回Council全WAIT、スコア78点出ても無視
  - strat+5(atr_breakout:66.7%)という「戦略がはまった瞬間」シグナルも黙殺
- **原因**: 白書方針「LLMのconfidenceは参考値のみ→Phase 4bで常に上書き」がverdict層では未実施
- **解決**: Phase 4c新設。calc_conf >= 65でBUY、<45でWAIT、45-64はLLM判定を尊重

### 🥈 RISK_ON_RIDE加点の修正
- 0 → +3（RISK_ON局面で中立扱いは積極姿勢と矛盾していた）

### 🥉 bt=HIGH連動戦略フィットボーナス
- 戦略勝率>=70%: +5追加
- 戦略勝率>=60%: +3追加
- 「戦略がはまった瞬間に取引」方針を数値に反映

---

## 🔴 現状数値（v6.5bd時点）

| 項目 | 値 |
|---|---|
| 勝率(FIFO) | 75.8% (33ペア決済) |
| USDC | $79,258.82 |
| Holdings | BTC(0.1177) |
| Evaluator 勝率 | 51.76% (85件) |
| 直近取引 | 2026/04/19（3日間無取引）|

---

## ⏭️ 次セッションの作業(優先順)

### 🥇 Phase 4c 効果観察
v6.5be改修後、初のBUY判断が出るか観察が必要。最低24〜72時間待つこと。
確認パターン:
- A: Phase 4c発火→BUY成功（理想）
- B: Phase 4c発火→Phase 5ガードで弾かれる
- C: Phase 4c発火せず（grade zone常態化）
- D: 過剰BUY（ガード不足）

### 🥈 Phase 5ガード通過率の確認
Phase 4cでBUY扱いになった後、どのガードでどれだけ弾かれるかの分布を取る。

### 🥉 triple_ma_cross tier=mid問題
100%勝率(2/2)なのにtier=mid(加点0)。サンプル数フィルタで意図的な挙動だが、
tier判定ロジックの見直しも今後検討。

---

## 📁 本セッションで変更したファイル

| 種別 | 場所 | 内容 |
|---|---|---|
| 編集 | agents/trinity_council.py | Phase 4c追加、RISK_ON_RIDE 0→+3、bt=HIGH連動fit bonus |
| バックアップ | .archive_deadcode_v65p/trinity_council.py.bak_v6.5be_verdict_override | ロールバック用 |
| 新規 | docs/GSD計画_v6.5be_引き継ぎ白書.md | 本ファイル |

---

## ロールバック手順

```bash
cd /docker/openclaw-taan/data/.openclaw/workspace && \
cp .archive_deadcode_v65p/trinity_council.py.bak_v6.5be_verdict_override agents/trinity_council.py && \
systemctl restart neo-radar.service
```
