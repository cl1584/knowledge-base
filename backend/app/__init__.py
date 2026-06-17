"""FastAPI 入口"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from sqlalchemy import text

from app.core.config import settings
from app.core.database import Base, engine
from app.api.auth import router as auth_router
from app.api.notes import router as notes_router
from app.api.chat import router as chat_router
from app.api.tags import router as tags_router
from app.api.users import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表 + 安全检查"""
    logger.info(f"🚀 启动 {settings.app_name} v{settings.version}")
    Base.metadata.create_all(bind=engine)
    logger.info(f"📁 SQLite: {settings.sqlite_path}")
    logger.info(f"📁 ChromaDB: {settings.chroma_path}")

    # 数据库迁移：给 users 表补加新列（v0.1.0 → v0.1.1）
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(users)")).fetchall()
        if result:   # 表存在才迁移
            cols = {row[1] for row in result}
            for col, sql_type in [
                ("ai_api_key", "TEXT DEFAULT ''"),
                ("ai_base_url", "VARCHAR(512) DEFAULT ''"),
                ("ai_model", "VARCHAR(128) DEFAULT ''"),
            ]:
                if col not in cols:
                    logger.info(f"🔧 迁移：users 表加列 {col}")
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {sql_type}"))
                    conn.commit()

    # 安全检查
    if settings.jwt_secret.startswith("change-me"):
        logger.warning("⚠️  JWT_SECRET 还在用默认值！生产环境务必改（.env）")
    if settings.deepseek_api_key and settings.deepseek_api_key.startswith("sk-your"):
        logger.warning("⚠️  DEEPSEEK_API_KEY 是占位符，请填真实 key")
    if not settings.deepseek_api_key and not settings.dashscope_api_key:
        logger.info("ℹ️  未配置 AI key，聊天走演示模式")

    yield
    logger.info("👋 关闭")


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

# CORS
# 注意：浏览器规范禁止 allow_origins=["*"] 同时 allow_credentials=True
# 这里根据配置自动切换：开发期 (DEBUG) 允许通配，生产期必须填具体域名
_cors_origins = settings.cors_origins
_cors_allow_all = "*" in _cors_origins
if _cors_allow_all and not settings.debug:
    # 生产环境误配 * 配 credentials 会让所有请求失败
    # 降级到只允许默认本地地址（开发用），生产前必须改 .env
    logger.warning("⚠️  CORS 配置是 * 但 DEBUG=false，浏览器会拒绝带凭证的请求。请在 .env 里填具体域名。")
    _cors_origins = ["http://localhost:5173"]
    _cors_allow_all = False
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=not _cors_allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 路由
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(notes_router, prefix="/api/notes", tags=["notes"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(tags_router, prefix="/api/tags", tags=["tags"])
app.include_router(users_router, prefix="/api/users", tags=["users"])


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
    }
