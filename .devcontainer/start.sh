#!/usr/bin/env bash
cd "$(dirname "$0")/.."
nohup python webui.py --noautoopen --port 7865 > /tmp/webui.log 2>&1 &
sleep 20
gh codespace ports visibility 7865:public -c "$CODESPACE_NAME" 2>/dev/null || true
