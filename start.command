#!/bin/bash
cd "$(dirname "$0")"
source venv/bin/activate

# Check if port 8972 is already in use
if lsof -i :8972 >/dev/null 2>&1; then
  osascript -e 'display dialog "端口 8972 已被占用，请先关闭占用的程序" buttons {"确定"} default button "确定" with title "MD→WPS 一键排版"'
  exit 1
fi

# Start uvicorn in background
python -m uvicorn app:app --host 0.0.0.0 --port 8972 &
SERVER_PID=$!

# Wait for server to start
sleep 2

# Open browser
open http://localhost:8972/

# Keep terminal open
echo "MD→WPS 一键排版已启动，按 Ctrl+C 停止服务"
wait $SERVER_PID
