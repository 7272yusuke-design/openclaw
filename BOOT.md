# 🚀 Neo Operations Guide (Hostinger VPS)

## 24/7 Deployment (常時稼働の掟)
カレントディレクトリのズレや、ログの出力停止を防ぐため、必ず絶対パスと非バッファモード(-u)で起動すること。

### 起動手順

1. ログフォルダの確保
mkdir -p /docker/openclaw-taan/data/.openclaw/workspace/logs

2. 古いプロセスの停止
pkill -f neo_daemon.py || true
pkill -f event_listener.py || true

3. バックグラウンド起動 (絶対パス + Unbuffered)
source /docker/openclaw-taan/data/.openclaw/workspace/neo-env/bin/activate && \
nohup python3 -u /docker/openclaw-taan/data/.openclaw/workspace/neo_daemon.py > /docker/openclaw-taan/data/.openclaw/workspace/logs/daemon.log 2>&1 & \
nohup python3 -u /docker/openclaw-taan/data/.openclaw/workspace/tools/event_listener.py > /docker/openclaw-taan/data/.openclaw/workspace/logs/listener.log 2>&1 &
