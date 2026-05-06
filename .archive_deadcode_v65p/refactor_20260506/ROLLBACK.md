# 緊急ロールバック手順 (refactor_20260506)

## seller_native_v2.ts を戻す
cp .archive_deadcode_v65p/refactor_20260506/seller_native_v2.ts.bak skills/acp-cli-v2/src/seller/seller_native_v2.ts
systemctl restart neo-acp-seller-v2.service
sleep 5
journalctl -u neo-acp-seller-v2.service --since "1 minute ago" --no-pager | head -20

## DRY_RUNに戻す(緊急時のみ)
sed -i 's/V2_SELLER_DRY_RUN=false/V2_SELLER_DRY_RUN=true/' /etc/systemd/system/neo-acp-seller-v2.service
systemctl daemon-reload
systemctl restart neo-acp-seller-v2.service

## archive済ファイルを戻す
mv .archive_deadcode_v65p/refactor_20260506/acp_executor_agent.py agents/  # Phase 2.4で archive した場合のみ
mv .archive_deadcode_v65p/refactor_20260506/openclaw-acp-v2 skills/        # Phase 2.3で archive した場合のみ
mv .archive_deadcode_v65p/refactor_20260506/v1_seller_runtime skills/virtuals-protocol-acp/src/seller/runtime  # Phase 2.5の場合

## git stash で全変更を退避
git stash
git stash list
