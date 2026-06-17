"""Tags API"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.core.database import get_db
from app.models import User, Tag, Note, NoteTag
from app.api.auth import get_current_user
from app.schemas import TagOut

router = APIRouter()


@router.get("", response_model=list[TagOut])
def list_tags(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出所有标签（按使用次数倒序）"""
    from sqlalchemy import func
    rows = (
        db.query(Tag, func.count(NoteTag.note_id).label("cnt"))
        .outerjoin(NoteTag, Tag.id == NoteTag.tag_id)
        .filter(Tag.user_id == current_user.id)
        .group_by(Tag.id)
        .order_by(desc("cnt"), Tag.name)
        .all()
    )
    result = []
    for tag, cnt in rows:
        out = TagOut.model_validate(tag)
        out.note_count = cnt
        result.append(out)
    return result


@router.post("", response_model=TagOut)
def create_tag(
    name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建标签（已存在则返回）"""
    name = (name or "").strip()
    if not name:
        raise HTTPException(400, "标签名不能为空")
    if len(name) > 32:
        raise HTTPException(400, "标签名最多 32 字符")
    existing = db.query(Tag).filter(Tag.user_id == current_user.id, Tag.name == name).first()
    if existing:
        return existing
    tag = Tag(user_id=current_user.id, name=name)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag


@router.delete("/{tag_id}")
def delete_tag(
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    tag = db.query(Tag).filter(Tag.id == tag_id, Tag.user_id == current_user.id).first()
    if not tag:
        raise HTTPException(404, "标签不存在")
    db.delete(tag)  # cascade 会删 note_tags
    db.commit()
    return {"ok": True}


@router.get("/by-note/{note_id}", response_model=list[TagOut])
def get_note_tags(
    note_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取某篇笔记的标签"""
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id, Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(404, "笔记不存在")
    return [TagOut.model_validate(t) for t in note.tags]


@router.put("/by-note/{note_id}")
def set_note_tags(
    note_id: int,
    tag_names: list[str],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """设置某篇笔记的标签（全量替换）"""
    note = db.query(Note).filter(
        Note.id == note_id, Note.user_id == current_user.id, Note.deleted_at.is_(None)
    ).first()
    if not note:
        raise HTTPException(404, "笔记不存在")

    # 规范化
    names = []
    for n in tag_names:
        n = (n or "").strip()
        if n and n not in names:
            names.append(n)
    names = names[:20]  # 最多 20 个标签

    # 清空旧关联
    db.query(NoteTag).filter(NoteTag.note_id == note_id).delete()

    # 找/建标签
    for name in names:
        tag = db.query(Tag).filter(Tag.user_id == current_user.id, Tag.name == name).first()
        if not tag:
            tag = Tag(user_id=current_user.id, name=name)
            db.add(tag)
            db.flush()
        db.add(NoteTag(note_id=note_id, tag_id=tag.id))

    db.commit()
    return {"ok": True, "tags": names}
