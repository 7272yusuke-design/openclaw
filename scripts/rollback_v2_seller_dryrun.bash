#!/bin/bash
# 緊急ロールバック: v2 seller を DRY_RUN に戻して再起動
set -e
echo "[ROLLBACK] V2 seller を DRY_RUN に戻します"
sed -i 's/^Environment=V2_SELLER_DRY_RUN=false$/Environment=V2_SELLER_DRY_RUN=true/' \
    /etc/systemd/system/neo-acp-seller-v2.service
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service
sleep 5
systemctl status neo-acp-seller-v2.service --no-pager | head -10
echo "[ROLLBACK] 完了。ログ確認: journalctl -u neo-acp-seller-v2.service -f"
