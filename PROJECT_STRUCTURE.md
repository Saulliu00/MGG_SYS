# MGG仿真系统 - 项目结构说明

## 📁 完整目录树

```
MGG_SYS/
│
├── 📄 README.md                    # 项目主文档
├── 📄 QUICKSTART.md                # 快速启动指南
├── 📄 PROJECT_STRUCTURE.md         # 本文件 - 项目结构说明
│
├── 🚀 run.py                       # 应用入口文件
├── 🚀 start.sh                     # Linux/Mac启动脚本
├── 🚀 start.bat                    # Windows启动脚本
│
├── ⚙️ config.py                     # 应用配置
├── 📦 requirements.txt             # Python依赖列表
├── 🔒 .env.example                 # 环境变量示例
├── 📝 .gitignore                   # Git忽略文件
│
├── 🐍 venv/                        # Python虚拟环境 (Python 3.12)
│
├── 📂 app/                         # 主应用目录
│   ├── __init__.py                # Flask应用初始化
│   ├── models.py                  # 数据库模型定义
│   │
│   ├── 📂 routes/                  # 路由蓝图
│   │   ├── __init__.py
│   │   ├── auth.py                # 用户认证路由
│   │   ├── main.py                # 主页路由
│   │   ├── simulation.py          # 仿真计算路由
│   │   └── admin.py               # 管理员路由
│   │
│   ├── 📂 static/                  # 静态文件
│   │   ├── 📂 css/
│   │   │   └── style.css          # 主样式文件
│   │   ├── 📂 js/
│   │   │   ├── simulation.js      # 仿真页面脚本
│   │   │   └── admin.js           # 管理页面脚本
│   │   └── 📂 uploads/            # 上传文件存储
│   │       └── .gitkeep
│   │
│   └── 📂 templates/               # HTML模板
│       ├── base.html              # 基础模板
│       ├── index.html             # 首页
│       ├── 📂 auth/
│       │   ├── login.html         # 登录页
│       │   └── register.html      # 注册页
│       ├── 📂 simulation/
│       │   ├── index.html         # 仿真主界面
│       │   └── history.html       # 历史记录页
│       └── 📂 admin/
│           └── index.html         # 管理面板
│
├── 📂 database/                    # 数据库文件目录
│   └── simulation_system.db      # SQLite数据库（运行后自动生成）
│
└── 📂 logs/                        # 日志文件目录
```

## 🏗️ 系统架构

### 四层架构

```
┌─────────────────────────────────────┐
│   Browser (Engineer/Admin)         │  用户界面层
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Web App (UI + Auth)               │  展示层
│   - Flask Templates                 │
│   - Bootstrap 5 UI                  │
│   - User Authentication             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Application Logic                 │  业务逻辑层
│   - Simulation Engine                │
│   - Data Processing                  │
│   - File Upload Handler             │
└─────────────────────────────────────┘
              ↓
┌─────────────────────────────────────┐
│   Database + File Storage           │  数据层
│   - SQLite Database                  │
│   - Uploaded Files                   │
└─────────────────────────────────────┘
```

## 📊 数据库模型

### User (用户表)
```python
- id: Integer (主键)
- username: String (用户名，唯一)
- email: String (邮箱，唯一)
- password_hash: String (密码哈希)
- is_admin: Boolean (是否为管理员)
- is_active: Boolean (账户是否激活)
- created_at: DateTime (创建时间)
```

### Simulation (仿真记录表)
```python
- id: Integer (主键)
- user_id: Integer (外键 -> User)
- ignition_model: String (点火具型号)
- nc_type_1: String (NC类型1)
- nc_usage_1: Float (NC用量1)
- nc_type_2: String (NC类型2)
- nc_usage_2: Float (NC用量2)
- gp_type: String (GP类型)
- gp_usage: Float (GP用量)
- shell_model: String (外壳型号)
- current: Float (电流)
- sensor_model: String (传感器型号)
- body_model: String (体积型号)
- equipment: String (设备)
- test_operator: String (测试操作员)
- test_name: String (测试名称)
- notes: Text (备注)
- result_data: Text (结果数据，JSON格式)
- chart_image: String (图表路径)
- created_at: DateTime (创建时间)
```

### TestResult (测试结果表)
```python
- id: Integer (主键)
- user_id: Integer (外键 -> User)
- simulation_id: Integer (外键 -> Simulation，可选)
- filename: String (文件名)
- file_path: String (文件路径)
- data: Text (测试数据，JSON格式)
- uploaded_at: DateTime (上传时间)
```

## 🛣️ 路由映射

### 认证路由 (`/auth`)
| 路由 | 方法 | 功能 |
|------|------|------|
| `/auth/login` | GET, POST | 用户登录 |
| `/auth/register` | GET, POST | 用户注册 |
| `/auth/logout` | GET | 退出登录 |

### 主页路由 (`/`)
| 路由 | 方法 | 功能 |
|------|------|------|
| `/` | GET | 系统首页 |

### 仿真路由 (`/simulation`)
| 路由 | 方法 | 功能 |
|------|------|------|
| `/simulation/` | GET | 仿真计算界面 |
| `/simulation/run` | POST | 执行仿真计算 |
| `/simulation/upload` | POST | 上传测试数据 |
| `/simulation/history` | GET | 查看历史记录 |

### 管理路由 (`/admin`) - 需要管理员权限
| 路由 | 方法 | 功能 |
|------|------|------|
| `/admin/` | GET | 管理面板首页 |
| `/admin/users` | GET | 用户列表 |
| `/admin/user/add` | POST | 添加用户 |
| `/admin/user/<id>/toggle` | POST | 切换用户状态 |
| `/admin/user/<id>/delete` | POST | 删除用户 |
| `/admin/user/<id>/reset-password` | POST | 重置密码 |

## 🎨 前端技术栈

- **HTML5**: 语义化标记
- **CSS3**: 自定义样式 + Bootstrap 5
- **JavaScript (ES6+)**:
  - 仿真计算交互
  - 文件上传处理
  - 图表绘制 (Plotly.js)
  - 管理面板功能
- **图表库**: Plotly.js
- **UI框架**: Bootstrap 5
- **图标**: Font Awesome 6

## 🔧 后端技术栈

- **Python 3.12**: 核心语言
- **Flask 3.0**: Web框架
- **SQLAlchemy**: ORM数据库操作
- **Flask-Login**: 用户会话管理
- **Flask-Bcrypt**: 密码加密
- **Pandas**: 数据处理
- **NumPy**: 数值计算
- **Plotly**: 图表生成

## 🔐 安全特性

1. **密码加密**: 使用Bcrypt哈希算法
2. **会话管理**: Flask-Login安全会话
3. **CSRF保护**: Flask-WTF表单保护
4. **SQL注入防护**: SQLAlchemy参数化查询
5. **文件上传验证**: 文件类型和大小限制
6. **角色权限控制**: 管理员/普通用户区分

## 📝 关键文件说明

### 后端文件

- **run.py**: 应用启动入口，运行Flask开发服务器
- **config.py**: 配置类定义，包含开发/生产环境配置
- **app/__init__.py**: Flask应用工厂，初始化扩展和蓝图
- **app/models.py**: 数据库模型定义

### 前端文件

- **templates/base.html**: 基础模板，包含导航栏和通用结构
- **static/css/style.css**: 全局样式，包含仿真界面专用样式
- **static/js/simulation.js**: 仿真计算、图表绘制、数据上传逻辑
- **static/js/admin.js**: 管理面板交互功能

### 配置文件

- **requirements.txt**: Python包依赖列表
- **.env.example**: 环境变量模板
- **.gitignore**: Git版本控制忽略规则

## 🚀 部署注意事项

### 开发环境
- 使用SQLite数据库
- DEBUG模式启用
- 端口: 5000

### 生产环境建议
- 切换到PostgreSQL/MySQL
- 关闭DEBUG模式
- 使用Gunicorn/uWSGI
- 配置Nginx反向代理
- 启用HTTPS
- 设置强SECRET_KEY
- 配置日志记录
- 定期数据库备份

## 📚 待实现功能

当前为UI原型版本，以下功能待开发：

1. **仿真算法**: 实际物理模型计算
2. **数据分析**: 统计分析、趋势预测
3. **报告生成**: PDF/Excel导出
4. **模型管理**: 模型版本控制
5. **批量处理**: 批量仿真计算
6. **API接口**: RESTful API
7. **实时监控**: WebSocket实时数据推送
8. **权限细化**: 更细粒度的权限控制

## 💡 开发建议

1. **添加新功能**: 在 `app/routes/` 创建新蓝图
2. **修改UI**: 编辑 `app/templates/` 中的HTML文件
3. **调整样式**: 修改 `app/static/css/style.css`
4. **添加数据模型**: 在 `app/models.py` 添加新类
5. **配置修改**: 编辑 `config.py`

## 🐛 调试技巧

1. 检查Flask日志: 终端输出
2. 浏览器开发者工具: 检查网络请求和控制台错误
3. 数据库查看: 使用SQLite浏览器工具
4. Python调试: 使用 `print()` 或 `pdb`

## 📞 技术支持

遇到问题请参考：
- [README.md](README.md) - 完整文档
- [QUICKSTART.md](QUICKSTART.md) - 快速启动
- Flask官方文档: https://flask.palletsprojects.com/
