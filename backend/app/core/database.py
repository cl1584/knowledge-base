"""数据库连接"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base, Session

from app.core.config import settings


# SQLite 需要 check_same_thread=False 以便 FastAPI 多线程访问
connect_args = {"check_same_thread": False} if "sqlite" in str(settings.sqlite_path) else {}

engine = create_engine(
    f"sqlite:///{settings.sqlite_path}",
    connect_args=connect_args,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：每个请求一个 Session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
