#!/bin/bash
set -e

# 课堂交互分析系统云端接收服务部署脚本

PROJECT_DIR="/root/video_project"
VENV_DIR="/root/venv"
SERVICE_PORT="${SERVICE_PORT:-8010}"

echo "[1/4] 进入项目目录"
cd "$PROJECT_DIR"

echo "[2/4] 激活虚拟环境"
source "$VENV_DIR/bin/activate"

echo "[3/4] 安装云端接收服务依赖"
pip install -r cloud_backend/requirements.txt

echo "[4/4] 启动云端接收服务"
exec uvicorn cloud_backend.main:app --host 0.0.0.0 --port "$SERVICE_PORT"
