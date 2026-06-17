# 个人 AI 知识库

> 一个自托管的个人知识库，部署在飞牛 NAS 上，支持 Windows 桌面端，对接 DeepSeek 实现 RAG 问答。

## 架构

```
┌──────────────────┐
│  Windows 客户端    │  Tauri + Vue 3 + Naive UI
└────────┬─────────┘
         │  HTTP
         ▼
┌──────────────────┐
│  FastAPI 后端     │  Python 3.12
│  ├─ Auth (JWT)   │
│  ├─ Notes CRUD   │
│  └─ Chat (RAG)   │
└────┬─────────┬───┘
     │         │
     ▼         ▼
┌────────┐ ┌─────────┐
│ SQLite │ │ChromaDB │
│ 笔记   │ │  向量   │
└────────┘ └─────────┘
                │
                ▼
       ┌────────────────┐
       │ DeepSeek API    │
       │ DashScope Embed │
       └────────────────┘
```

## 当前进度

- [x] **Phase 1：后端核心**
  - [x] FastAPI 项目结构
  - [x] SQLite + SQLAlchemy 模型
  - [x] JWT 鉴权（注册 / 登录 / 当前用户）
  - [x] 笔记 CRUD API
  - [x] ChromaDB + Embedding 集成
  - [x] DeepSeek 流式对话
  - [x] RAG 检索
  - [x] 单元测试
  - [x] Dockerfile + docker-compose
- [x] **Phase 2：Windows 客户端**（Tauri + Vue 3）
  - [x] 登录 / 笔记 CRUD / AI 对话 / 设置
  - [x] 模型预设（6 个：DeepSeek/OpenAI/通义/Claude/Ollama/自定义）
  - [x] 性能优化（路由守卫 / 分页 / 乐观更新 / 快捷键）
  - [x] NSIS 安装包（1.7 MB）
- [x] **Phase 3：CI/CD**（GitHub Actions）
  - [x] 自动打后端 Docker 镜像（push to ghcr.io）
  - [x] 自动打 Tauri Windows 安装包（artifact / release）
- [x] **Phase 4：NAS 一键部署**
  - [x] `scripts/install-on-nas.sh`（拉镜像 + 起容器 + Caddy + 备份）
- [ ] **Phase 5：实盘部署到你的飞牛 NAS**

## 快速部署到 NAS（推荐方式）

GitHub Actions 自动构建后，**在 NAS 上跑一行**：
```bash
curl -fsSL https://raw.githubusercontent.com/你的用户名/knowledge-base/main/scripts/install-on-nas.sh | sudo KB_IMAGE=ghcr.io/你的用户名/knowledge-base-backend:latest bash
```

具体见 [docs/DEPLOY.md](docs/DEPLOY.md)。

## 快速开始（开发模式）

```bash
cd backend
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入 DEEPSEEK_API_KEY / DASHSCOPE_API_KEY

uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

## 跑测试

```bash
cd backend
pytest -v
```

## 部署到飞牛 NAS

见 [docs/DEPLOY.md](docs/DEPLOY.md)。推荐流程：

1. **本机**：把项目推到 GitHub（`git init` → 远程 → `git push`）
2. **GitHub Actions 自动**：后端镜像推到 ghcr.io + Tauri .exe 推到 Releases
3. **NAS 上一行命令**：拉镜像 + 起容器 + 自动 HTTPS + 每日备份

## 文件结构

```
knowledge-base/
├── backend/                      # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py          # FastAPI 入口
│   │   ├── core/                # 配置、数据库、安全
│   │   ├── models/              # SQLAlchemy 模型
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── api/                 # 路由
│   │   │   ├── auth.py          # 登录注册
│   │   │   ├── notes.py         # 笔记 CRUD
│   │   │   ├── chat.py          # AI 对话（SSE）
│   │   │   ├── tags.py          # 标签
│   │   │   └── users.py         # 用户设置
│   │   ├── services/            # RAG / Embedding / LLM
│   │   └── tasks/               # 异步任务（向量化）
│   ├── data/                    # SQLite + ChromaDB
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── windows-client/               # Tauri 2 + Vue 3 客户端
│   ├── src/                     # Vue 源码
│   ├── src-tauri/               # Rust 容器
│   ├── build.ps1                # 一键打包脚本
│   └── dist/                    # 打包后的 web 资源
├── .github/workflows/           # CI/CD
│   ├── backend-image.yml        # 自动打后端镜像
│   └── tauri-windows.yml        # 自动打 Tauri 安装包
├── scripts/
│   └── install-on-nas.sh        # NAS 一键安装
├── docs/
│   ├── DEPLOY.md                # 部署指南
│   └── BUILD.md                 # 打包指南
└── README.md
```

## 安全注意

- **JWT_SECRET**：生产前用 `openssl rand -hex 32` 改写
- **API key**：`.env` 已在 `.gitignore` 中，不会被提交。**绝不要把真实 key 写进代码或 commit**
- **CORS**：生产环境必须改成具体域名（默认 `*` 在 `allow_credentials=true` 时浏览器会拒绝）
- **登录限流**：单 worker 有效 5 次/分钟；多 worker 部署需要 Redis
- **JWT 存 localStorage**：有 XSS 风险，Tauri 内 WebView 比浏览器安全一些

## 规划文档

完整规划见 `~/.claude/plans/golden-finding-newell.md`。
UI 原型见 `knowledge-base.html`。
