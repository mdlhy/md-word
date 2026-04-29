#!/bin/bash
cd "$(dirname "$0")"

if [ ! -f "venv/bin/activate" ]; then
    echo "正在创建虚拟环境..."
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo "创建虚拟环境失败，请确认已安装 Python 3.10+"
        exit 1
    fi
fi

source venv/bin/activate

if ! pip show fastapi > /dev/null 2>&1; then
    echo "正在安装依赖..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "安装依赖失败"
        exit 1
    fi
fi

if ss -tlnp 2>/dev/null | grep -q ':8972 '; then
    echo "端口 8972 已被占用，请先关闭占用的程序"
    exit 1
elif netstat -tlnp 2>/dev/null | grep -q ':8972 '; then
    echo "端口 8972 已被占用，请先关闭占用的程序"
    exit 1
fi

echo "正在启动 MD→WPS 一键排版..."

python -m uvicorn app:app --host 0.0.0.0 --port 8972 &
SERVER_PID=$!

sleep 2

if command -v xdg-open > /dev/null 2>&1; then
    xdg-open http://localhost:8972/
elif command -v sensible-browser > /dev/null 2>&1; then
    sensible-browser http://localhost:8972/
else
    echo "请手动打开浏览器访问: http://localhost:8972/"
fi

echo "MD→WPS 一键排版已启动，按 Ctrl+C 停止服务"
wait $SERVER_PID
