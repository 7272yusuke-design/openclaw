#!/bin/bash
# v6.5be Phase 4c 効果観察ダッシュボード

cd /docker/openclaw-taan/data/.openclaw/workspace

echo "============================================================"
echo "📊 v6.5be Phase 4c 観察ダッシュボード $(date)"
echo "============================================================"

echo ""
echo "--- ① サービス状態 ---"
for svc in neo-radar neo-collector neo-resource-api neo-acp-seller; do
    status=$(systemctl is-active $svc.service)
    echo "  $svc: $status"
done

echo ""
echo "--- ② Phase 4c 発火統計 ---"
total_councils=$(grep -c "\[Phase 4b\] ルールベース再計算" radar_output.log)
phase4c_fires=$(grep -c "\[Phase 4c\] ⚡ verdict上書き" radar_output.log)
phase4c_buy=$(grep -c "\[Phase 4c\] ⚡ verdict上書き.*Rule=BUY" radar_output.log)
phase4c_wait=$(grep -c "\[Phase 4c\] ⚡ verdict上書き.*Rule=WAIT" radar_output.log)
echo "  総Council数: $total_councils"
echo "  Phase 4c上書き回数: $phase4c_fires"
echo "  うちBUY上書き: $phase4c_buy"
echo "  うちWAIT上書き: $phase4c_wait"

echo ""
echo "--- ③ 直近10回のverdict推移 ---"
grep -E "\[Phase 4\] JSON判定|\[Phase 4b\] ルールベース再計算|\[Phase 4c\]|\[Phase 5\]" radar_output.log | tail -20

echo ""
echo "--- ④ PaperWallet状態 ---"
./neo-env/bin/python -c "
import sys; sys.path.insert(0,'.')
from tools.paper_wallet import PaperWallet
pw = PaperWallet()
hist = pw.state.get('history', [])
print(f'  取引総数: {len(hist)}件')
print(f'  USDC: \${pw.state[\"usd_balance\"]:,.2f}')
print(f'  最新5件:')
for h in hist[-5:]:
    ts = h.get('timestamp','?')[:19]
    print(f\"    {ts} | {h.get('action')} {h.get('symbol')} @ \${h.get('price')}\")
"

echo ""
echo "--- ⑤ D3移行条件トラッキング ---"
./neo-env/bin/python -c "
import sys; sys.path.insert(0,'.')
from tools.paper_wallet import PaperWallet
from datetime import datetime, timezone
pw = PaperWallet()
hist = pw.state.get('history', [])

reset_ts = '2026-04-03T00:00:00'
post_reset = [h for h in hist if h.get('timestamp','') >= reset_ts]

buy_q = {}; wins = 0; losses = 0
for h in post_reset:
    s = h.get('symbol','')
    if h['action'] == 'BUY': buy_q.setdefault(s,[]).append(float(h['price']))
    elif h['action'] == 'SELL' and buy_q.get(s):
        if float(h['price']) > buy_q[s].pop(0): wins += 1
        else: losses += 1

total_closed = wins + losses
winrate = wins/total_closed*100 if total_closed else 0
print(f'  リセット後取引: {len(post_reset)}件')
print(f'  決済済ペア: {total_closed}件')
print(f'  勝率: {winrate:.1f}% (必要: 60%以上)')
print(f'  取引100回まで: あと{max(0,100-total_closed)}ペア')

reset_dt = datetime(2026,4,3, tzinfo=timezone.utc)
now = datetime.now(timezone.utc)
days = (now - reset_dt).days
print(f'  リセット後経過: {days}日 (必要: 90日以上、最短移行日 2026/06/14)')
"

echo ""
echo "--- ⑥ 直近エラー/警告 ---"
grep -iE "error|exception|traceback" radar_output.log | tail -3

echo ""
echo "============================================================"
