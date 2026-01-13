#!/bin/bash

echo "================================"
echo "MGG仿真系统 - 安装验证脚本"
echo "================================"
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "检查 Python 版本..."
if command -v python3.12 &> /dev/null; then
    PYTHON_VERSION=$(python3.12 --version)
    echo -e "${GREEN}✓${NC} $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3.12 未找到"
    exit 1
fi

# Check virtual environment
echo ""
echo "检查虚拟环境..."
if [ -d "venv" ]; then
    echo -e "${GREEN}✓${NC} 虚拟环境已创建"
else
    echo -e "${YELLOW}!${NC} 虚拟环境未找到，正在创建..."
    python3.12 -m venv venv
    echo -e "${GREEN}✓${NC} 虚拟环境创建成功"
fi

# Check directories
echo ""
echo "检查项目目录..."
REQUIRED_DIRS=("app" "app/routes" "app/static" "app/templates" "database" "logs")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo -e "${GREEN}✓${NC} $dir/"
    else
        echo -e "${RED}✗${NC} $dir/ 缺失"
        mkdir -p "$dir"
        echo -e "${YELLOW}!${NC} 已创建 $dir/"
    fi
done

# Check key files
echo ""
echo "检查关键文件..."
REQUIRED_FILES=("run.py" "config.py" "requirements.txt" "app/__init__.py" "app/models.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✓${NC} $file"
    else
        echo -e "${RED}✗${NC} $file 缺失"
    fi
done

# Summary
echo ""
echo "================================"
echo "验证完成！"
echo "================================"
echo ""
echo "下一步："
echo "1. 运行 ./start.sh 启动应用"
echo "2. 访问 http://localhost:5000"
echo "3. 使用账号 admin / admin123 登录"
echo ""
