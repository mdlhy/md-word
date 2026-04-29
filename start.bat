@echo off
chcp 65001 >nul 2>&1
cd /d "%~dp0"

if not exist "venv\Scripts\activate.bat" (
    echo 正在创建虚拟环境...
    python -m venv venv
    if errorlevel 1 (
        echo 创建虚拟环境失败，请确认已安装 Python 3.10+
        pause
        exit /b 1
    )
)

call venv\Scripts\activate.bat

pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 安装依赖失败
        pause
        exit /b 1
    )
)

netstat -ano | findstr ":8972 " | findstr "LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo 端口 8972 已被占用，请先关闭占用的程序
    pause
    exit /b 1
)

echo 正在启动 MD→WPS 一键排版...
start http://localhost:8972/
python -m uvicorn app:app --host 0.0.0.0 --port 8972
