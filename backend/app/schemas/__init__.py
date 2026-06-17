"""Pydantic Schemas（API 数据结构）"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


# ========== Auth ==========
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    nickname: Optional[str] = Field("", max_length=64)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


# ========== User / AI Settings ==========
class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    nickname: str = ""
    avatar: str = ""
    has_ai_key: bool = False       # 是否配置了 AI API Key（不返回 key 本身）
    ai_base_url: str = ""
    ai_model: str = ""
    created_at: datetime


class AISettingsUpdate(BaseModel):
    """用户保存自己的 AI 设置（api_key=None 表示不修改）"""
    api_key: Optional[str] = None   # None=不修改；""=清除；其他=写入新 key
    base_url: str = ""
    model: str = ""


class AISettingsResponse(BaseModel):
    """返回当前 AI 设置（不含 key 明文）"""
    has_key: bool
    base_url: str = ""
    model: str = ""


# ========== Note ==========
class NoteBase(BaseModel):
    title: str = Field("", max_length=255)
    content: str = ""


class NoteCreate(NoteBase):
    pass


class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    content: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None


class NoteOut(NoteBase):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    is_pinned: bool
    is_archived: bool
    created_at: datetime
    updated_at: datetime


class NoteListResponse(BaseModel):
    items: List[NoteOut]
    total: int
    has_more: bool


# ========== Chat (RAG) ==========
class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(8, ge=1, le=20)
    conversation_id: Optional[int] = None   # 多轮对话（v1 暂用最近 N 条）


class ChatChunk(BaseModel):
    """流式返回的单个 chunk"""
    type: str   # start / delta / done / error
    content: Optional[str] = None
    references: Optional[List[dict]] = None   # 引用的笔记
    is_demo: Optional[bool] = None
    error: Optional[str] = None


# ========== Tag ==========
class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    note_count: int = 0  # 关联的笔记数（运行时填充）


TokenResponse.model_rebuild()
