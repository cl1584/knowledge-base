"""数据库模型"""
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Index
)
from sqlalchemy.orm import relationship

from app.core.database import Base


def now_utc():
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    nickname = Column(String(64), default="")
    avatar = Column(String(512), default="")
    # AI 设置（每用户可覆盖系统默认）
    ai_api_key = Column(Text, default="")       # 明文存储（本地 SQLite，属主即用户）
    ai_base_url = Column(String(512), default="")
    ai_model = Column(String(128), default="")
    created_at = Column(DateTime, default=now_utc, nullable=False)
    last_login_at = Column(DateTime, default=now_utc)

    notes = relationship("Note", back_populates="user", cascade="all, delete-orphan")
    tags = relationship("Tag", back_populates="user", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

    @property
    def has_ai_key(self) -> bool:
        return bool(self.ai_api_key and self.ai_api_key.strip())


class Note(Base):
    __tablename__ = "notes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), default="")
    content = Column(Text, default="")
    content_hash = Column(String(64), index=True)   # 用于检测变更，避免重复向量化
    source = Column(String(32), default="windows")   # windows / web
    is_pinned = Column(Boolean, default=False, index=True)
    is_archived = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=now_utc, nullable=False, index=True)
    updated_at = Column(DateTime, default=now_utc, onupdate=now_utc, nullable=False, index=True)
    deleted_at = Column(DateTime, nullable=True, index=True)

    user = relationship("User", back_populates="notes")
    tags = relationship("Tag", secondary="note_tags", back_populates="notes")

    __table_args__ = (
        Index("ix_notes_user_updated", "user_id", "updated_at"),
    )


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime, default=now_utc)

    user = relationship("User", back_populates="tags")
    notes = relationship("Note", secondary="note_tags", back_populates="tags")


class NoteTag(Base):
    __tablename__ = "note_tags"

    note_id = Column(Integer, ForeignKey("notes.id", ondelete="CASCADE"), primary_key=True)
    tag_id = Column(Integer, ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True)


class Conversation(Base):
    """AI 对话历史（v1 暂存于本地也 OK）"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(16), nullable=False)   # user / assistant
    content = Column(Text, nullable=False)
    referenced_notes = Column(Text, default="")  # JSON: [note_id, ...]
    created_at = Column(DateTime, default=now_utc, nullable=False, index=True)

    user = relationship("User", back_populates="conversations")
