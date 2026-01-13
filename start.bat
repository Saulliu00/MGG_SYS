@echo off
echo MGG仿真系统启动脚本
echo ====================

REM Check if virtual environment exists
if not exist "venv\" (
    echo 虚拟环境不存在，正在创建...
    python -m venv venv
)

REM Activate virtual environment
echo 激活虚拟环境...
call venv\Scripts\activate.bat

REM Install/Update dependencies
echo 检查并安装依赖...
pip install -r requirements.txt

REM Create database directory if it doesn't exist
if not exist "database\" mkdir database

REM Run the application
echo 启动应用...
echo 访问地址: http://localhost:5000
echo 默认管理员账号: admin / admin123
echo ====================
python run.py

pause
