# MGG仿真系统 (MGG Simulation System)

基于Python Flask的Web仿真系统，用于点火具测试参数配置、仿真计算、实际数据对比分析。

## 系统架构

```
Browser (Engineer/Admin)
        ↓
Web App (UI + Auth)
        ↓
Application Logic (Simulation + Data)
        ↓
Database + File Storage
```

## 主要功能

1. **用户认证系统**
   - 用户登录/注册
   - 基于角色的访问控制（管理员/普通用户）
   - 管理员可管理用户账户

2. **仿真计算**
   - 测试参数配置（点火具型号、NC类型、GP类型等）
   - 实时仿真计算
   - PT曲线图表展示

3. **数据管理**
   - 上传实际测试数据（.xlsx格式）
   - 仿真数据与实际数据对比
   - 历史记录查询

4. **管理功能**
   - 用户添加/删除
   - 用户状态启用/禁用
   - 密码重置

## 技术栈

- **后端**: Python 3.12, Flask
- **数据库**: SQLite (可扩展至PostgreSQL/MySQL)
- **前端**: HTML5, CSS3, JavaScript, Bootstrap 5
- **图表**: Plotly.js
- **数据处理**: Pandas, NumPy

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

编辑 `.env` 文件，设置您的密钥：
```
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///database/simulation_system.db
FLASK_ENV=development
```

### 5. 初始化数据库

数据库会在首次运行时自动创建。默认管理员账户将自动生成：
- 用户名: `admin`
- 密码: `admin123`

### 6. 运行应用

```bash
python run.py
```

应用将在 `http://localhost:5000` 启动

## 目录结构

```
MGG_SYS/
├── app/
│   ├── __init__.py          # Flask应用初始化
│   ├── models.py            # 数据库模型
│   ├── routes/              # 路由蓝图
│   │   ├── auth.py          # 认证路由
│   │   ├── main.py          # 主页路由
│   │   ├── simulation.py    # 仿真路由
│   │   └── admin.py         # 管理路由
│   ├── static/              # 静态文件
│   │   ├── css/
│   │   │   └── style.css    # 样式文件
│   │   ├── js/
│   │   │   ├── simulation.js
│   │   │   └── admin.js
│   │   └── uploads/         # 上传文件存储
│   └── templates/           # HTML模板
│       ├── base.html
│       ├── index.html
│       ├── auth/
│       │   ├── login.html
│       │   └── register.html
│       ├── simulation/
│       │   ├── index.html
│       │   └── history.html
│       └── admin/
│           └── index.html
├── database/                # 数据库文件
├── logs/                    # 日志文件
├── venv/                    # Python虚拟环境
├── config.py               # 配置文件
├── run.py                  # 应用入口
├── requirements.txt        # Python依赖
└── README.md              # 项目文档
```

## 使用指南

### 首次登录

1. 访问 `http://localhost:5000`
2. 使用默认管理员账户登录：
   - 用户名: `admin`
   - 密码: `admin123`
3. **重要**: 登录后请立即修改管理员密码

### 仿真计算流程

1. 登录系统后，点击"仿真计算"
2. 在左侧面板配置测试参数：
   - 点火具型号
   - NC类型和用量
   - GP类型和用量
   - 外壳型号、电流等
3. 在中间面板填写测试信息：
   - 测试操作员
   - 测试名称
   - 备注
4. 点击"计算"按钮运行仿真
5. 结果将在右侧图表中显示

### 上传实际数据

1. 在"实际数据存储"标签页
2. 点击上传区域，选择.xlsx文件
   - 文件应包含两列：时间(Time)和压力(Pressure)
3. 点击"上传并存储"
4. 切换到"PT曲线对比"查看仿真与实际数据对比

### 管理员功能

1. 点击导航栏"管理面板"
2. 可执行以下操作：
   - 添加新用户
   - 启用/禁用用户账户
   - 重置用户密码
   - 删除用户

## API端点

### 认证
- `POST /auth/login` - 用户登录
- `POST /auth/register` - 用户注册
- `GET /auth/logout` - 退出登录

### 仿真
- `GET /simulation/` - 仿真界面
- `POST /simulation/run` - 运行仿真
- `POST /simulation/upload` - 上传测试数据
- `GET /simulation/history` - 查看历史记录

### 管理
- `GET /admin/` - 管理面板
- `POST /admin/user/add` - 添加用户
- `POST /admin/user/<id>/toggle` - 切换用户状态
- `POST /admin/user/<id>/delete` - 删除用户
- `POST /admin/user/<id>/reset-password` - 重置密码

## 数据库模型

### User (用户)
- id: 主键
- username: 用户名（唯一）
- email: 邮箱（唯一）
- password_hash: 密码哈希
- is_admin: 管理员标志
- is_active: 账户状态
- created_at: 创建时间

### Simulation (仿真记录)
- id: 主键
- user_id: 用户外键
- 测试参数字段（ignition_model, nc_type_1, etc.）
- test_operator: 测试操作员
- test_name: 测试名称
- notes: 备注
- result_data: 结果数据（JSON）
- created_at: 创建时间

### TestResult (测试结果)
- id: 主键
- user_id: 用户外键
- simulation_id: 关联仿真ID（可选）
- filename: 文件名
- file_path: 文件路径
- data: 测试数据（JSON）
- uploaded_at: 上传时间

## 后续开发计划

当前版本为UI原型，后续需要实现：

1. **仿真算法集成**
   - 实现实际的物理仿真模型
   - 参数优化算法
   - 模型训练功能

2. **数据分析**
   - 统计分析工具
   - 趋势预测
   - 报告生成

3. **系统优化**
   - 性能优化
   - 缓存机制
   - 异步任务处理

4. **部署**
   - 生产环境配置
   - Docker容器化
   - CI/CD流程

## 安全注意事项

1. 在生产环境中修改 `SECRET_KEY`
2. 使用强密码策略
3. 定期备份数据库
4. 启用HTTPS
5. 配置防火墙规则

## 许可证

内部使用项目

## 联系方式

如有问题请联系开发团队
