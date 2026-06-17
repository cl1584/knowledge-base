"""笔记向量化任务（FastAPI BackgroundTasks 调度，函数本身同步）"""
from loguru import logger

from app.services import get_vector_store


def index_note(note_id: int, user_id: int):
    """把指定笔记向量化入库（同步执行，调用方负责调度）"""
    from app.core.database import SessionLocal
    from app.models import Note

    db = SessionLocal()
    try:
        note = db.query(Note).filter(Note.id == note_id, Note.user_id == user_id).first()
        if not note:
            logger.warning(f"index_note: 笔记 {note_id} 不存在或不属于 user {user_id}")
            return
        vs = get_vector_store()
        vs.index_note(note.id, note.user_id, note.title, note.content)
    except Exception as e:
        logger.exception(f"向量化失败 note={note_id}: {e}")
    finally:
        db.close()


def delete_note_vectors(note_id: int, user_id: int):
    """删除指定笔记的所有向量"""
    try:
        vs = get_vector_store()
        vs.delete_note(note_id, user_id)
    except Exception as e:
        logger.exception(f"删除向量失败 note={note_id}: {e}")
