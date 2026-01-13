# 📑 MGG仿真系统 - 完整项目索引

## 🎯 快速导航

### 想要演示给客户？
→ 进入 [demo/](demo/) 文件夹，双击 `demo.html`

### 想要运行实际系统？
→ 运行 `./start.sh` (Mac/Linux) 或 `start.bat` (Windows)

### 想要了解项目结构？
→ 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)

### 想要快速开始？
→ 阅读 [QUICKSTART.md](QUICKSTART.md)

---

## 📁 项目文件导航

### 🎬 演示文件（给客户看）
```
demo/
├── demo.html           ⭐ 双击打开演示
├── README.md           演示文件夹说明
├── DEMO_GUIDE.md       完整演示指南
├── QUICK_START.txt     快速参考卡
└── DEMO_README.txt     简要说明
```

### 🚀 启动脚本
```
start.sh                Mac/Linux启动脚本
start.bat               Windows启动脚本
verify.sh               安装验证脚本
run.py                  Python启动文件
```

### 📚 文档
```
README.md               完整项目文档
QUICKSTART.md           快速启动指南
PROJECT_STRUCTURE.md    项目结构详解
SUMMARY.md              项目总结
INDEX.md                本文件 - 项目索引
```

### 💻 应用代码
```
app/
├── __init__.py         Flask应用初始化
├── models.py           数据库模型
├── routes/             路由蓝图
│   ├── auth.py         认证路由
│   ├── main.py         主页路由
│   ├── simulation.py   仿真路由
│   └── admin.py        管理路由
├── static/             静态文件
│   ├── css/style.css   样式文件
│   ├── js/simulation.js 仿真脚本
│   └── js/admin.js     管理脚本
└── templates/          HTML模板
    ├── base.html       基础模板
    ├── index.html      首页
    ├── auth/           认证页面
    ├── simulation/     仿真页面
    └── admin/          管理页面
```

### ⚙️ 配置文件
```
config.py               应用配置
requirements.txt        Python依赖
.env.example            环境变量模板
.gitignore              Git忽略规则
```

### 📦 数据与环境
```
venv/                   Python虚拟环境
database/               数据库文件目录
logs/                   日志文件目录
```

---

## 🎯 使用场景指南

### 场景1: 客户演示
**目标**: 展示完整UI和功能

1. 进入 `demo/` 文件夹
2. 双击 `demo.html`
3. 按照 `QUICK_START.txt` 进行演示
4. 参考 `DEMO_GUIDE.md` 获取演示话术

**时间**: 5-10分钟  
**需要**: 浏览器 + 网络连接  
**特点**: 无需安装，立即演示

---

### 场景2: 开发环境运行
**目标**: 运行完整系统进行开发

1. 打开终端，进入项目目录
2. 运行 `./start.sh` (或 `start.bat`)
3. 访问 http://localhost:5000
4. 使用 admin/admin123 登录

**时间**: 首次5分钟，之后30秒  
**需要**: Python 3.12  
**特点**: 完整前后端，可开发

---

### 场景3: 部署到生产
**目标**: 部署给实际用户使用

1. 阅读 `README.md` 的部署章节
2. 修改 `config.py` 为生产配置
3. 使用 Gunicorn + Nginx
4. 配置HTTPS和域名

**时间**: 1-2小时  
**需要**: 服务器 + 域名  
**特点**: 生产级部署

---

### 场景4: 集成仿真算法
**目标**: 将实际算法集成到系统

1. 打开 `app/routes/simulation.py`
2. 找到 `run_simulation()` 函数
3. 替换第35-43行的模拟数据
4. 实现真实的仿真计算逻辑

**位置**: [app/routes/simulation.py:20-45](app/routes/simulation.py)  
**需要**: 仿真算法的Python实现  
**特点**: 清晰的接口，易于集成

---

## 📊 项目统计

```
Python文件:      9个
HTML模板:        7个
CSS文件:         1个
JavaScript文件:  2个
文档文件:        8个（包括demo文件夹）

总代码行数:      ~1,857行
总文档字数:      ~15,000字
```

---

## 🔍 快速查找

### 找不到某个功能？

| 想找... | 看这里 |
|---------|--------|
| 登录逻辑 | [app/routes/auth.py](app/routes/auth.py) |
| 仿真计算 | [app/routes/simulation.py](app/routes/simulation.py) |
| 用户管理 | [app/routes/admin.py](app/routes/admin.py) |
| 数据库模型 | [app/models.py](app/models.py) |
| 主界面样式 | [app/static/css/style.css](app/static/css/style.css) |
| 图表绘制 | [app/static/js/simulation.js](app/static/js/simulation.js) |
| 仿真UI | [app/templates/simulation/index.html](app/templates/simulation/index.html) |
| 配置项 | [config.py](config.py) |

---

## ❓ 常见问题

### Q1: 如何快速演示给客户？
**A**: 进入 `demo/` 文件夹，双击 `demo.html`

### Q2: 如何启动开发服务器？
**A**: 运行 `./start.sh` (Mac/Linux) 或 `start.bat` (Windows)

### Q3: 默认管理员账号是什么？
**A**: 用户名 `admin`，密码 `admin123`

### Q4: 如何添加新功能？
**A**: 
1. 在 `app/routes/` 创建新路由文件
2. 在 `app/templates/` 创建对应模板
3. 在 `app/__init__.py` 注册蓝图

### Q5: 仿真算法在哪里实现？
**A**: [app/routes/simulation.py](app/routes/simulation.py) 的 `run_simulation()` 函数

### Q6: 如何修改数据库结构？
**A**: 修改 [app/models.py](app/models.py)，然后删除 `database/` 文件夹重新初始化

### Q7: 如何自定义样式？
**A**: 编辑 [app/static/css/style.css](app/static/css/style.css)

### Q8: 支持什么数据库？
**A**: 默认SQLite，可切换到PostgreSQL/MySQL

---

## 🎓 学习路径

### 新手入门
1. 阅读 [QUICKSTART.md](QUICKSTART.md)
2. 运行 `./start.sh`
3. 浏览界面，熟悉功能
4. 查看 [README.md](README.md) 了解详情

### 开发者
1. 阅读 [PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md)
2. 查看 `app/` 目录下的代码
3. 理解Flask蓝图和路由
4. 修改和扩展功能

### 演示者
1. 阅读 `demo/DEMO_GUIDE.md`
2. 练习 5步演示流程
3. 准备演示话术
4. 双击 `demo/demo.html` 开始演示

---

## 📞 获取帮助

### 文档优先级
1. **快速问题** → `QUICKSTART.md`
2. **演示相关** → `demo/DEMO_GUIDE.md`
3. **详细信息** → `README.md`
4. **架构问题** → `PROJECT_STRUCTURE.md`
5. **项目概览** → `SUMMARY.md`

---

## ✅ 验证清单

运行前检查：
- [ ] Python 3.12 已安装
- [ ] 虚拟环境已创建 (`venv/` 文件夹存在)
- [ ] 依赖已安装 (运行过 `pip install -r requirements.txt`)
- [ ] 端口 5000 未被占用

演示前检查：
- [ ] 网络连接正常
- [ ] 浏览器已安装（Chrome/Edge推荐）
- [ ] `demo/demo.html` 可以正常打开
- [ ] 已阅读 `demo/QUICK_START.txt`

---

**需要帮助？参考对应的文档文件！** 📚

