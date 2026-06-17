"""Notes API：笔记 CRUD + 搜索 + 同步"""
import hashlib
import html
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc

from app.core.database import get_db
from app.models import User, Note
from app.schemas import NoteCreate, NoteUpdate, NoteOut, NoteListResponse
from app.api.auth import get_current_user
from app.tasks.indexer import index_note, delete_note_vectors

router = APIRouter()


def _hash_content(title: str, content: str) -> str:
    return hashlib.sha256(f"{title}\n{content}".encode("utf-8")).hexdigest()


def _sanitize_text(text: str) -> str:
    """轻度清洗：去 null 字节、控制字符；HTML 转义留给前端 (DOMPurify)
    这里只做最基础的清理，避免存储污染"""
    if not text:
        return ""
    # 去掉 null 字节和常见控制字符（保留换行 / 制表）
    return "".join(
        ch for ch in text
        if ch == "\n" or ch == "\t" or ch == "\r" or ord(ch) >= 0x20
    )


@router.post("", response_model=NoteOut)
def create_note(
    req: NoteCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建笔记"""
    clean_title = _sanitize_text(req.title).strip() or "未命名笔记"
    clean_content = _sanitize_text(req.content)
    note = Note(
        user_id=current_user.id,
        title=clean_title,
        content=clean_content,
        content_hash=_hash_content(clean_title, clean_content),
        source="windows",
    )
    db.add(note)
    db.commit()
    db.refresh(note)
    # 异步触发向量化（FastAPI BackgroundTasks，请求结束后执行）
    background_tasks.add_task(index_note, note.id, current_user.id)
    return note


@router.get("", response_model=NoteListResponse)
def list_notes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    keyword: Optional[str] = Query(None, max_length=200),
    is_archived: bool = False,
    include_deleted: bool = False,   # true 时只返回已删除（恢复用）
    tag_id: Optional[list[int]] = Query(None, alias="tag_id"),  # 多选
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    since: Optional[datetime] = None,   # 增量同步：拉取 updated_at > since
):
    """获取笔记列表（按更新时间倒序）"""
    q = db.query(Note).filter(Note.user_id == current_user.id)
    if include_deleted:
        q = q.filter(Note.deleted_at.is_not(None))
    else:
        q = q.filter(Note.deleted_at.is_(None))
        q = q.filter(Note.is_archived == is_archived)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.filter(or_(Note.title.like(kw), Note.content.like(kw)))
    if tag_id:
        # 包含任一标签的笔记（OR 关系）
        from app.models import NoteTag
        q = q.join(NoteTag, Note.id == NoteTag.note_id).filter(NoteTag.tag_id.in_(tag_id)).distinct()
    if since:
        q = q.filter(Note.updated_at > since)
    total = q.count()
    items = q.order_by(desc(Note.is_pinned), desc(Note.updated_at)).offset(offset).limit(limit).all()
    return NoteListResponse(items=items, total=total, has_more=offset + len(items) < total)


@router.get("/{note_id}", response_model=NoteOut)
def get_note(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id, Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    return note


@router.patch("/{note_id}", response_model=NoteOut)
def update_note(
    note_id: int,
    req: NoteUpdate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新笔记（自动检测内容变化触发重新向量化）"""
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id, Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")

    new_title = req.title if req.title is not None else note.title
    new_content = req.content if req.content is not None else note.content
    content_changed = (new_title != note.title) or (new_content != note.content)

    if req.title is not None:
        note.title = _sanitize_text(req.title).strip() or "未命名笔记"
    if req.content is not None:
        note.content = _sanitize_text(req.content)
    if req.is_pinned is not None:
        note.is_pinned = req.is_pinned
    if req.is_archived is not None:
        note.is_archived = req.is_archived

    if content_changed:
        note.content_hash = _hash_content(note.title, note.content)
    db.commit()
    db.refresh(note)

    if content_changed:
        background_tasks.add_task(index_note, note.id, current_user.id)
    return note


@router.delete("/{note_id}")
def delete_note(
    note_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    permanent: bool = False,
):
    """删除笔记（默认软删，permanent=true 硬删）"""
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不存在")
    if permanent:
        db.delete(note)
        background_tasks.add_task(delete_note_vectors, note_id, current_user.id)
    else:
        note.deleted_at = datetime.now(timezone.utc)
    db.commit()
    return {"ok": True}


@router.post("/{note_id}/restore", response_model=NoteOut)
def restore_note(
    note_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """从已删除列表恢复笔记"""
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id, Note.deleted_at.is_not(None)
    ).first()
    if not note:
        raise HTTPException(status_code=404, detail="笔记不在已删除列表中")
    note.deleted_at = None
    db.commit()
    db.refresh(note)
    # 重新向量化
    background_tasks.add_task(index_note, note.id, current_user.id)
    return note
