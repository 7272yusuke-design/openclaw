#!/bin/bash
# Restore pre-native-SDK state
set -e
cd /docker/openclaw-taan/data/.openclaw/workspace
echo "Restoring seller runtime..."
rm -rf skills/virtuals-protocol-acp/src/seller/runtime/
cp -r .archive_pre_native_sdk/runtime_backup/ skills/virtuals-protocol-acp/src/seller/runtime/
echo "Restoring config.json..."
cp .archive_pre_native_sdk/config.json.backup skills/virtuals-protocol-acp/config.json
echo "Restoring package.json..."
cp .archive_pre_native_sdk/package.json.backup skills/virtuals-protocol-acp/package.json
echo "Restoring .env..."
cp .archive_pre_native_sdk/env.backup .env
echo "Restarting neo-acp-seller..."
systemctl restart neo-acp-seller.service
echo "Done. Restored to OpenClaw runtime."
