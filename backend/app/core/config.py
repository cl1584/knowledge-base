"""应用配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    """从 .env 文件和环境变量加载配置"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # 基础
    app_name: str = "个人 AI 知识库"
    debug: bool = True
    version: str = "0.1.0"

    # 数据存储
    data_dir: Path = Path("./data")
    sqlite_path: Path = Path("./data/kb.db")
    chroma_path: Path = Path("./data/chroma")

    # 鉴权
    jwt_secret: str = "change-me-in-production-please-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24 * 30  # 30 天

    # DeepSeek（LLM）
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"

    # DashScope（Embedding，可选）
    dashscope_api_key: str = ""
    embedding_model: str = "text-embedding-v2"
    embedding_dim: int = 1536

    # RAG 参数
    # chunk_size: 中文字符约 1 字符/字，800-1000 适合笔记类长文
    # chunk_overlap: 至少 10% 防止切断语义边界
    chunk_size: int = 1000
    chunk_overlap: int = 120
    retrieval_top_k: int = 8

    # CORS
    # 生产环境必须填具体域名（例：["https://kb.yourdomain.com"]）
    # "*" 仅在 allow_credentials=false 时合法，本项目用 cookie 鉴权时会冲突
    cors_origins: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:1420",
        "http://localhost:1420",
        "tauri://localhost",
    ]


settings = Settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)
