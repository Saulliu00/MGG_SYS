# 快速启动指南

## 方法一：使用启动脚本（推荐）

### macOS/Linux
```bash
./start.sh
```

### Windows
双击运行 `start.bat` 或在命令行中执行：
```cmd
start.bat
```

## 方法二：手动启动

### 1. 激活虚拟环境

**macOS/Linux:**
```bash
source venv/bin/activate
```

**Windows:**
```cmd
venv\Scripts\activate
```

### 2. 安装依赖（首次运行）
```bash
pip install -r requirements.txt
```

### 3. 启动应用
```bash
python run.py
```

## 访问系统

1. 打开浏览器访问: **http://localhost:5000**

2. 使用默认管理员账号登录:
   - 用户名: `admin`
   - 密码: `admin123`

3. **重要**: 首次登录后请修改默认密码！

## 主要功能入口

- **仿真计算**: 导航栏 → 仿真计算
- **历史记录**: 导航栏 → 历史记录
- **用户管理**: 导航栏 → 管理面板（仅管理员可见）

## 常见问题

### 端口被占用
如果5000端口被占用，可以修改 `run.py` 中的端口号：
```python
app.run(debug=True, host='0.0.0.0', port=8000)  # 改为8000或其他端口
```

### Python版本问题
本系统需要Python 3.12，检查版本：
```bash
python3.12 --version
```

### 依赖安装失败
尝试升级pip：
```bash
pip install --upgrade pip
```

然后重新安装依赖：
```bash
pip install -r requirements.txt
```

## 停止应用

在终端中按 `Ctrl + C` 停止应用

## 系统要求

- Python 3.12+
- 8GB RAM（推荐）
- 1GB 磁盘空间
- 现代浏览器（Chrome, Firefox, Safari, Edge）

## 下一步

参考完整文档 [README.md](README.md) 了解详细功能和使用方法
