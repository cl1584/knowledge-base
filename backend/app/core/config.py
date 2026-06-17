"""应用配置"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
from pathlib import Path
import json


def _parse_cors_origins(v):
    """
    支持三种来源：
    1. list（python 代码里直接写）
    2. JSON 字符串（.env 里写 CORS_ORIGINS=["a","b"]）
    3. 逗号分隔（.env 里写 CORS_ORIGINS=https://a.com,https://b.com）
    """
    if isinstance(v, list):
        return v
    if not isinstance(v, str):
        return []
    s = v.strip()
    if not s:
        return []
    if s.startswith("["):
        # JSON 数组
        try:
            parsed = json.loads(s)
            return [str(x).strip() for x in parsed if str(x).strip()]
        except Exception:
            return []
    # 逗号分隔
    return [x.strip() for x in s.split(",") if x.strip()]


class Settings(BaseSettings):
    """从 .env 文件和环境变量加载配置"""

    # ⚠️ extra='ignore' 允许 .env 里塞任何调试用的变量（LOG_LEVEL / PYTHONUNBUFFERED / TZ 等）
    # pydantic 2 默认 forbid 会让容器内常见变量（LOG_LEVEL=INFO）启动失败
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
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
    # 环境变量 CORS_ORIGINS 可以覆盖：
    #   - JSON 数组：CORS_ORIGINS=["https://a.com","https://b.com"]
    #   - 逗号分隔：CORS_ORIGINS=https://a.com,https://b.com
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:5173",
            "http://127.0.0.1:1420",
            "http://localhost:1420",
            "tauri://localhost",
        ],
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _v_cors(cls, v):
        return _parse_cors_origins(v)


settings = Settings()

# 确保数据目录存在
settings.data_dir.mkdir(parents=True, exist_ok=True)
settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
settings.chroma_path.mkdir(parents=True, exist_ok=True)
