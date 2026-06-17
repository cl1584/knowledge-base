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

- [x] **Phase 1：后端核心** ← 进行中
  - [x] FastAPI 项目结构
  - [x] SQLite + SQLAlchemy 模型
  - [x] JWT 鉴权（注册 / 登录 / 当前用户）
  - [x] 笔记 CRUD API
  - [x] ChromaDB + Embedding 集成
  - [x] DeepSeek 流式对话
  - [x] RAG 检索
  - [x] 单元测试
  - [ ] Docker 镜像验证
- [ ] **Phase 2：Windows 客户端**（Tauri + Vue 3）
- [ ] **Phase 4：AI/RAG 集成优化**
- [ ] **Phase 5：飞牛 NAS 部署**

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

见 `docs/DEPLOY.md`（待写）。

## 文件结构

```
knowledge-base/
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── __init__.py        # FastAPI 入口
│   │   ├── core/              # 配置、数据库、安全
│   │   ├── models/            # SQLAlchemy 模型
│   │   ├── schemas/           # Pydantic schemas
│   │   ├── api/               # 路由
│   │   │   ├── auth.py        # 登录注册
│   │   │   ├── notes.py       # 笔记 CRUD
│   │   │   └── chat.py        # AI 对话（SSE）
│   │   ├── services/          # RAG / Embedding / LLM
│   │   └── tasks/             # 异步任务（向量化）
│   ├── data/                  # SQLite + ChromaDB
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── docs/
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
