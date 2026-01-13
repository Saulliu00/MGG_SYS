#!/bin/bash

echo "MGG仿真系统启动脚本"
echo "===================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "虚拟环境不存在，正在创建..."
    python3.12 -m venv venv
fi

# Activate virtual environment
echo "激活虚拟环境..."
source venv/bin/activate

# Install/Update dependencies
echo "检查并安装依赖..."
pip install -r requirements.txt

# Create database directory if it doesn't exist
mkdir -p database

# Run the application
echo "启动应用..."
echo "访问地址: http://localhost:5000"
echo "默认管理员账号: admin / admin123"
echo "===================="
python run.py
