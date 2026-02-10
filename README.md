# MGG仿真系统 (MGG Simulation System)

基于Python Flask的Web仿真系统，用于点火具测试参数配置、仿真计算、实际数据对比分析。

[![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/)
[![Flask](https://img.shields.io/badge/flask-2.x-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/license-Internal-red.svg)]()

## ⚠️ IMPORTANT: Demo Folder Isolation

**The `demo/` folder is completely isolated and independent from the main project.**

- Demo is for quick demonstrations only
- Demo does NOT use main project code (app/, models/, etc.)
- Main project changes do NOT affect demo functionality
- Demo is self-contained with its own HTML, scripts, and data

See [demo/README_ISOLATION.md](demo/README_ISOLATION.md) for complete isolation policy.

---

## 系统架构

```
Browser (Multi-User, Local Network)
        ↓
Load Balancer / Reverse Proxy (Optional)
        ↓
Web App (Flask + Gunicorn)
   ├── Authentication & Authorization
   ├── Request Logging & Timeout Middleware
   ├── Service Layer (Simulation, File, Comparison)
   └── Health Monitoring
        ↓
┌───────────────────┬──────────────────┬──────────────────┐
│   Database        │   File Storage   │   System Logs    │
│   (SQLite/Pg)     │   (Uploads)      │   (CSV Files)    │
└───────────────────┴──────────────────┴──────────────────┘
```

## 主要功能

### 1. **用户认证系统**
   - 用户登录/注册/登出
   - 三级角色访问控制：
     - **Admin** - 全系统访问权限
     - **实验工程师** (Lab Engineer) - 仅访问实验结果
     - **研发工程师** (R&D Engineer) - 访问正向/逆向仿真
   - 每日登录要求（每天0点自动过期，需重新登录）
   - 安全特性：HTTPOnly cookies, 开放重定向防护, 路径遍历防护
   - 失败登录尝试日志记录

### 2. **仿真计算**
   - 测试参数配置（点火具型号、NC类型/用量、GP类型/用量、管壳高度、电流、传感器量程、容积等）
   - 自定义输入支持（所有下拉菜单支持自定义值）
   - 工单号自动生成
   - 实时仿真计算（120秒超时保护）
   - **Plotly交互式PT曲线图表**
   - 多项式拟合与峰值压力分析
   - 仿真结果自动存储

### 3. **数据管理**
   - 上传实际测试数据（.xlsx格式，60秒超时）
   - **仿真数据与实际数据PT曲线对比**
   - 统计分析（RMSE, 相关系数, 峰值差异）
   - 实验结果页面（批量文件上传、拖拽上传）
   - Excel文件验证与处理

### 4. **管理功能**
   - 用户添加/删除/启用/禁用（支持角色分配）
   - 密码重置
   - **系统日志查看器**（CSV格式，路径遍历防护）
   - 日志文件下载
   - 系统健康监控

### 5. **网络与多用户支持**
   - 局域网多用户访问
   - CORS配置（可自定义允许源）
   - 连接池管理（最大100并发连接）
   - Gunicorn生产部署配置
   - 请求超时保护
   - 慢请求自动记录（>5秒）

### 6. **系统监控与日志**
   - **CSV格式系统日志**（每日轮转）
   - 30GB存储限制自动清理
   - 用户操作审计追踪
   - 健康检查端点（`/health`）
   - 性能指标记录
   - 错误追踪与堆栈跟踪

### 7. **自动化功能**
   - 系统Logo自动生成
   - 日志文件自动轮转（每日）
   - 旧日志自动清理（90天保留期）
   - 数据库自动初始化
   - 默认管理员账户创建

## 技术栈

### 后端
- **Python 3.12**
- **Flask** 2.x - Web框架
- **Flask-Login** - 用户会话管理
- **Flask-Bcrypt** - 密码哈希
- **Flask-CORS** - 跨域资源共享
- **SQLAlchemy** - ORM数据库访问
- **Gunicorn** - 生产WSGI服务器

### 前端
- **HTML5, CSS3, JavaScript (ES6+)**
- **Bootstrap 5** - UI框架
- **Plotly.js** - 交互式图表
- **Font Awesome** - 图标库

### 数据处理
- **Pandas** - 数据分析
- **NumPy** - 数值计算
- **OpenPyXL** - Excel文件处理

### 图形与可视化
- **Plotly (Python)** - 后端图表生成
- **PIL (Pillow)** - Logo生成

## 安装步骤

### 1. 克隆或进入项目目录

```bash
cd MGG_SYS
```

### 2. 激活虚拟环境

#### macOS/Linux:
```bash
source venv/bin/activate
```

#### Windows:
```bash
venv\Scripts\activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 创建环境变量文件（可选）

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置您的配置：
```env
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///instance/simulation_system.db
CORS_ORIGINS=*  # 或指定IP范围，如 http://192.168.1.0/24
```

### 5. 初始化数据库

数据库会在首次运行时自动创建。默认管理员账户将自动生成：
- **用户名**: `admin`
- **密码**: `admin123`
- ⚠️ **重要**: 首次登录后请立即修改密码

### 6. 运行应用

#### 开发环境:
```bash
python run.py
```
应用将在 `http://0.0.0.0:5001` 启动（可从局域网访问）

#### 生产环境 (推荐):
```bash
gunicorn -c gunicorn.conf.py run:app
```

详细部署说明请参考 [NETWORK_DEPLOYMENT.md](NETWORK_DEPLOYMENT.md)

## 目录结构

```
MGG_SYS/
├── app/
│   ├── __init__.py              # Flask应用工厂
│   ├── models.py                # 数据库模型
│   ├── config/                  # 配置文件
│   │   ├── network_config.py    # 网络与多用户配置
│   │   ├── plot_config.py       # 图表样式配置
│   │   └── logging_config.py    # 日志系统配置
│   ├── routes/                  # 路由蓝图
│   │   ├── auth.py              # 认证路由（登录/登出/注册）
│   │   ├── main.py              # 主页与健康检查
│   │   ├── simulation.py        # 仿真与文件上传
│   │   └── admin.py             # 用户管理与日志查看
│   ├── services/                # 业务逻辑层
│   │   ├── simulation_service.py    # 仿真服务
│   │   ├── file_service.py          # 文件处理服务
│   │   └── comparison_service.py    # PT曲线对比服务
│   ├── middleware/              # 中间件
│   │   ├── timeout.py           # 请求超时中间件
│   │   └── logging_middleware.py    # 日志记录中间件
│   ├── utils/                   # 工具函数
│   │   ├── paths.py             # 路径管理
│   │   ├── errors.py            # 自定义异常
│   │   ├── responses.py         # 响应格式化
│   │   ├── validators.py        # 数据验证
│   │   ├── file_handler.py      # 文件处理
│   │   ├── subprocess_runner.py # 子进程管理
│   │   ├── plotter.py           # Plotly图表生成
│   │   ├── logo_generator.py    # Logo生成器
│   │   └── log_manager.py       # 日志管理器
│   ├── static/                  # 静态文件
│   │   ├── css/
│   │   │   └── style.css        # 自定义样式
│   │   ├── js/
│   │   │   ├── simulation.js    # 仿真页面脚本
│   │   │   └── admin.js         # 管理页面脚本
│   │   ├── assets/
│   │   │   └── logos/           # 系统Logo（自动生成）
│   │   │       ├── mgg_logo.png
│   │   │       └── favicon.ico
│   │   └── uploads/             # 用户上传文件
│   ├── templates/               # HTML模板
│   │   ├── base.html            # 基础模板
│   │   ├── auth/
│   │   │   ├── login.html
│   │   │   └── register.html
│   │   ├── simulation/
│   │   │   ├── index.html       # 正向仿真
│   │   │   ├── reverse.html     # 逆向仿真
│   │   │   └── history.html     # 实验结果（批量上传）
│   │   └── admin/
│   │       ├── index.html       # 用户管理
│   │       └── logs.html        # 系统日志查看器
│   └── log/                     # 系统日志（CSV格式）
│       ├── .gitignore
│       └── mgg_system_log_YYYY-MM-DD.csv
├── demo/                        # 独立演示环境（隔离）
├── models/                      # 仿真模型文件
├── instance/                    # 实例文件（数据库）
├── gunicorn.conf.py            # Gunicorn生产配置
├── config.py                   # Flask配置
├── run.py                      # 应用入口
├── requirements.txt            # Python依赖
├── README.md                   # 项目文档（本文件）
└── NETWORK_DEPLOYMENT.md       # 网络部署指南
```

## 使用指南

### 首次登录

1. 访问 `http://localhost:5001`（或服务器IP地址）
2. 使用默认管理员账户登录：
   - 用户名: `admin`
   - 密码: `admin123`
3. **重要**: 登录后请立即前往"用户管理"修改密码

### 仿真计算流程

1. 登录系统后，点击侧边栏 **"MGG → 正向"**
2. 在左侧"测试参数"面板配置：
   - 点火具型号、NC类型/用量（毫克）、GP类型/用量（毫克）
   - 管壳高度（mm）、电流、传感器量程、容积
   - 所有下拉菜单支持"自定义..."输入
3. 在中间"测试标准与人员"面板填写：
   - 工号（选填）
   - 测试名称（选填）
   - 备注（选填）
   - 测试设备（选填）
   - 点击"生成工单"创建工单号
4. 点击 **"计算"** 按钮运行仿真
5. 仿真结果将在右侧显示：
   - **PT曲线图表**（交互式Plotly图表）
   - 拟合统计信息（R²值、峰值压力）

### 上传实际测试数据

1. 切换到 **"实际数据存储"** 标签页
2. 点击上传区域，选择 `.xlsx` 文件
   - 文件格式要求：
     - 第一列：Time (时间，单位：ms)
     - 第二列：Pressure (压力，单位：MPa)
     - 前4行为表头/元数据（自动跳过）
3. 文件选择后自动上传
4. 切换到 **"PT曲线对比"** 标签页查看：
   - 仿真曲线（蓝色实线）
   - 实际测试曲线（红色虚线）
   - 对比统计指标

### 查看系统日志（管理员）

1. 点击侧边栏 **"Access Control → 系统日志"**
2. 查看日志统计仪表板：
   - 日志文件总数
   - 存储空间使用情况（/ 30GB）
   - 当前活动日志文件
3. 浏览日志文件列表
4. 点击 **"查看"** 查看日志详情
5. 点击 **"下载"** 下载CSV文件进行离线分析

### 管理用户账户（管理员）

1. 点击侧边栏 **"Access Control → 用户管理"**
2. 可执行操作：
   - **添加新用户** - 填写用户名、工号、密码、角色（Admin/实验工程师/研发工程师）
   - **启用/禁用** - 切换用户账户状态
   - **重置密码** - 为用户设置新密码
   - **删除用户** - 永久删除用户账户

## API端点

### 认证
| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/auth/login` | GET/POST | 否 | 用户登录 |
| `/auth/register` | GET/POST | 否 | 用户注册 |
| `/auth/logout` | GET | 否 | 退出登录 |

### 仿真
| 端点 | 方法 | 认证 | 角色 | 说明 |
|------|------|------|------|------|
| `/simulation/` | GET | 是 | Admin/研发 | 正向仿真界面 |
| `/simulation/reverse` | GET | 是 | Admin/研发 | 逆向仿真界面 |
| `/simulation/run` | POST | 是 | 全部 | 运行仿真计算 |
| `/simulation/upload` | POST | 是 | 全部 | 上传测试数据 |
| `/simulation/history` | GET | 是 | Admin/实验 | 实验结果页面 |
| `/simulation/experiment` | POST | 是 | Admin/实验 | 提交实验数据（批量上传） |
| `/simulation/predict` | POST | 是 | 全部 | 运行快速预测 |
| `/simulation/generate_comparison_chart` | POST | 是 | 全部 | 生成PT对比图表 |

### 管理
| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/admin/` | GET | 管理员 | 管理面板 |
| `/admin/user/add` | POST | 管理员 | 添加用户 |
| `/admin/user/<id>/toggle` | POST | 管理员 | 切换用户状态 |
| `/admin/user/<id>/delete` | POST | 管理员 | 删除用户 |
| `/admin/user/<id>/reset-password` | POST | 管理员 | 重置密码 |
| `/admin/logs` | GET | 管理员 | 系统日志页面 |
| `/admin/logs/view` | GET | 管理员 | 查看日志内容 |
| `/admin/logs/download/<filename>` | GET | 管理员 | 下载日志文件 |

### 系统
| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/health` | GET | 否 | 健康检查（返回JSON状态） |

## 数据库模型

### User (用户)
```python
- id: Integer, PrimaryKey
- username: String(80), Unique, NotNull
- employee_id: String(120), Unique, NotNull  # 工号
- password_hash: String(128), NotNull
- role: String(20), NotNull, Default='research_engineer'
  # 'admin' | 'lab_engineer' | 'research_engineer'
- is_active: Boolean, Default=True
- created_at: DateTime, Default=now()
```

### Simulation (仿真记录)
```python
- id: Integer, PrimaryKey
- user_id: Integer, ForeignKey(User)
- ignition_model: String(50)       # 点火具型号
- nc_type_1/2/3: String(50)        # NC类型
- nc_usage_1/2/3: Float            # NC用量 (毫克)
- gp_type_1/2/3: String(50)        # GP类型
- gp_usage_1/2/3: Float            # GP用量 (毫克)
- shell_model: String(50)          # 管壳高度 (mm)
- current: Float                   # 电流
- sensor_model: String(50)         # 传感器量程
- body_model: String(50)           # 容积
- equipment: String(50)            # 测试设备
- employee_id: String(100)         # 工号
- test_name: String(200)           # 测试名称
- notes: Text                      # 备注
- work_order: String(50)           # 工单号
- result_data: JSON
- created_at: DateTime
```

### TestResult (测试结果)
```python
- id: Integer, PrimaryKey
- user_id: Integer, ForeignKey(User)
- simulation_id: Integer, ForeignKey(Simulation), Nullable
- filename: String(255)
- file_path: String(500)
- data: JSON
- uploaded_at: DateTime
```

## 系统日志

系统自动记录以下事件到CSV文件（`app/log/mgg_system_log_YYYY-MM-DD.csv`）：

### 记录的事件类型
- ✅ 系统启动/关闭
- ✅ 用户登录/登出（成功和失败）
- ✅ 用户注册
- ✅ 仿真运行（参数和结果）
- ✅ 文件上传（文件名、大小、状态）
- ✅ 慢请求（>5秒）
- ✅ 失败请求（4xx, 5xx错误）
- ✅ 异常错误（含堆栈跟踪）

### CSV日志格式
```csv
timestamp,date,time,level,username,user_id,ip_address,method,endpoint,path,status_code,duration_ms,action,message,error,traceback,user_agent,request_id
```

### 日志管理
- **轮转**: 每日创建新文件
- **存储限制**: 30GB最大值
- **自动清理**: 超过限制时删除最旧文件
- **保留期**: 最少保留90天
- **访问**: 管理员可通过Web界面查看和下载

## 网络配置

### 局域网访问

1. **查找服务器IP地址**:
   ```bash
   # Linux
   ip addr show

   # Windows
   ipconfig

   # macOS
   ifconfig
   ```

2. **从其他设备访问**:
   - URL格式: `http://<服务器IP>:5001`
   - 示例: `http://192.168.1.100:5001`

3. **防火墙配置**:
   ```bash
   # Ubuntu/Debian
   sudo ufw allow 5001/tcp

   # CentOS/RHEL
   sudo firewall-cmd --add-port=5001/tcp --permanent
   sudo firewall-cmd --reload
   ```

### 生产部署

参考 [NETWORK_DEPLOYMENT.md](NETWORK_DEPLOYMENT.md) 获取完整部署指南，包括:
- Gunicorn配置
- Systemd服务设置
- Docker部署
- 负载均衡配置
- 性能调优
- 安全加固

## 配置选项

### 网络配置 (`app/config/network_config.py`)

```python
# 请求超时
TIMEOUTS = {
    'default_request': 30,      # 默认30秒
    'simulation': 120,          # 仿真120秒
    'file_upload': 60,          # 上传60秒
}

# CORS配置
CORS_CONFIG = {
    'origins': '*',  # 或设置特定IP范围
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
}

# Worker配置（生产环境）
WORKER_CONFIG = {
    'workers': os.cpu_count() * 2 + 1,  # 自动计算
    'threads': 4,
    'timeout': 30,
}
```

### 日志配置 (`app/config/logging_config.py`)

```python
# 日志轮转
LOG_ROTATION = {
    'frequency': 'daily',       # daily, hourly, on_reboot
    'max_folder_size_gb': 30,   # 30GB限制
}

# 记录事件
LOG_EVENTS = {
    'user_login': True,
    'simulation_run': True,
    'file_upload': True,
    'slow_requests': True,      # >5秒的请求
    'failed_requests': True,    # 4xx和5xx
    'all_requests': False,      # 设为True记录所有请求
}
```

## 性能优化

### 推荐配置

**开发环境**:
- Flask开发服务器
- SQLite数据库
- 单worker

**生产环境**:
- Gunicorn + Nginx
- PostgreSQL/MySQL数据库
- 多worker (CPU核心数 * 2 + 1)
- Redis缓存（可选）

### 监控

系统提供以下监控端点:

```bash
# 健康检查
curl http://localhost:5001/health

# 日志统计
curl http://localhost:5001/admin/logs/statistics
```

响应示例:
```json
{
  "status": "healthy",
  "checks": {
    "database": "ok",
    "file_system": "ok"
  }
}
```

## 安全最佳实践

### 生产环境清单

- [ ] 修改默认管理员密码
- [ ] 设置强SECRET_KEY（环境变量）
- [ ] 启用HTTPS（设置SESSION_COOKIE_SECURE=True）
- [ ] 限制CORS源（不使用'*'）
- [ ] 配置防火墙规则
- [ ] 定期备份数据库
- [ ] 定期审查系统日志
- [ ] 使用强密码策略
- [ ] 配置fail2ban防暴力破解
- [ ] 定期更新依赖包

### 密码安全

系统使用Bcrypt进行密码哈希，推荐密码策略:
- 最少8个字符
- 包含大小写字母、数字和特殊符号
- 定期更换密码

## 故障排除

### 常见问题

**问题**: 无法从其他设备访问

**解决方案**:
1. 确认服务器绑定到`0.0.0.0`而非`127.0.0.1`
2. 检查防火墙是否允许5001端口
3. 确认设备在同一网络
4. 验证IP地址正确

**问题**: 仿真超时

**解决方案**:
- 在`app/config/network_config.py`中增加`simulation`超时值
- 检查模型文件是否存在
- 查看系统日志了解详细错误

**问题**: 日志文件过大

**解决方案**:
- 系统会自动清理超过30GB的日志
- 手动删除旧日志: `rm app/log/mgg_system_log_2025-*.csv`
- 调整保留期: 修改`logging_config.py`中的`keep_days`

### 日志查看

```bash
# 查看今日日志
cat app/log/mgg_system_log_$(date +%Y-%m-%d).csv

# 查找错误
grep ",ERROR," app/log/*.csv

# 查找特定用户操作
grep "username,admin" app/log/*.csv

# 统计日志行数
wc -l app/log/*.csv
```

## 版本历史

### v1.3 (2026-02-07)
- ✨ 三级角色访问控制（Admin/实验工程师/研发工程师）
- ✨ 每日登录要求（0点自动过期）
- ✨ 实验结果页面重新设计（双面板布局、批量文件上传）
- ✨ 工单号自动生成功能
- ✨ 所有下拉菜单支持自定义输入
- ✨ UI标签更新（管壳高度、传感器量程、容积、工号）
- 🔒 修复开放重定向漏洞
- 🔒 修复日志下载路径遍历漏洞
- 🔒 所有API端点添加认证保护
- 🐛 修复自定义下拉菜单值无法提交的问题
- 🐛 修复字段名不匹配（test_operator → employee_id）
- 🗑️ 清理无用JS函数

### v1.2 (2026-01-31)
- ✨ 添加CSV格式系统日志（日志轮转与30GB自动清理）
- ✨ 添加网络配置与多用户支持
- ✨ 添加自动Logo生成系统
- ✨ 添加Gunicorn生产部署配置
- ✨ 添加健康检查端点
- ✨ 添加请求超时中间件
- ✨ 添加管理员日志查看器

### v1.1 (2026-01-29)
- ✨ 添加Plotly图表可视化
- ✨ 实现服务层架构重构
- ✨ 添加PT曲线对比功能
- 🐛 修复登录页面样式问题

### v1.0 (2026-01-26)
- 🎉 初始版本发布
- ✅ 用户认证系统
- ✅ 仿真计算功能
- ✅ 数据上传与管理
- ✅ 管理员面板

## 后续开发计划

### 短期目标
- [ ] 添加数据导出功能（PDF报告）
- [ ] 自定义输入值自动保存到数据库配置表
- [ ] 实现高级统计分析

### 长期目标
- [ ] 机器学习模型优化
- [ ] PostgreSQL数据库迁移（参考 `database/` 文档）
- [ ] 移动端响应式优化
- [ ] API文档（Swagger/OpenAPI）

## 技术支持

### 文档资源
- [Flask官方文档](https://flask.palletsprojects.com/)
- [Plotly Python文档](https://plotly.com/python/)
- [Gunicorn文档](https://docs.gunicorn.org/)
- [网络部署指南](NETWORK_DEPLOYMENT.md)

### 问题反馈

如遇到问题或有功能建议:
1. 查看系统日志: `/admin/logs`
2. 检查健康状态: `GET /health`
3. 联系开发团队

## 许可证

内部使用项目 - 版权所有

## 致谢

感谢所有为本项目做出贡献的开发者和测试人员。

---

**最后更新**: 2026-02-07
**维护团队**: MGG开发组
