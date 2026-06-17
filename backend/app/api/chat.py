"""Chat API：基于知识库的 AI 对话（流式）"""
import json
from typing import AsyncIterator, List, Tuple
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from loguru import logger

from app.core.database import get_db
from app.models import User, Conversation
from app.api.auth import get_current_user
from app.schemas import ChatRequest
from app.services import get_vector_store, get_llm_for_user

router = APIRouter()


def _get_recent_history(user_id: int, limit: int = 6) -> List[Tuple[str, str]]:
    """取最近 N 轮对话，返回 [(role, content), ...]，按时间正序"""
    from app.core.database import SessionLocal
    db = SessionLocal()
    try:
        rows = (
            db.query(Conversation)
            .filter(Conversation.user_id == user_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
            .all()
        )
        rows = list(reversed(rows))
        return [(r.role, r.content) for r in rows]
    finally:
        db.close()


def build_rag_prompt(question: str, retrieved: list, history: list = None) -> Tuple[str, str]:
    """构造 RAG prompt（支持多轮历史）"""
    history = history or []

    if retrieved:
        ctx_parts = []
        for i, r in enumerate(retrieved, 1):
            ctx_parts.append(f"[{i}] {r['title']}\n{r['content']}")
        context_text = "\n\n".join(ctx_parts)
        system = (
            "你是一个用户的个人知识助手。基于用户提供的笔记内容回答问题。"
            "回答时引用相关笔记的序号（如 [1]）。如果笔记中没有相关信息，"
            "请明确说「知识库中未找到相关内容」。回答简洁有条理。"
        )
        user_parts = [f"参考笔记：\n{context_text}"]
    else:
        system = "你是一个友好的助手。用户问题可能与他的知识库无关。"
        user_parts = []

    if history:
        history_lines = []
        for role, content in history:
            label = "用户" if role == "user" else "AI"
            short = content[:300] + ("..." if len(content) > 300 else "")
            history_lines.append(f"{label}：{short}")
        user_parts.append("对话历史：\n" + "\n".join(history_lines))

    user_parts.append(f"当前问题：{question}")
    user = "\n\n".join(user_parts)
    return system, user


async def _stream_chat(user: User, req: ChatRequest) -> AsyncIterator[str]:
    """SSE 流式生成回答"""
    try:
        vs = get_vector_store()
        llm = get_llm_for_user(user)

        # 0. 取最近 N 轮对话历史（多轮上下文）
        history = _get_recent_history(user.id, limit=6)
        logger.info(f"📜 历史 {len(history)} 条")

        # 1. 检索：混合策略（关键词 + 可选 embedding）
        # 1a. 关键词检索（必走，零依赖）
        kw_hits = vs.search_by_keywords(user.id, req.question, top_k=req.top_k)
        # 1b. 向量检索（如果 embedding 可用）
        try:
            vec_hits = vs.search(user.id, req.question, top_k=req.top_k)
        except Exception as e:
            logger.warning(f"向量检索失败：{e}")
            vec_hits = []

        # 1c. 合并去重：按 note_id 去重（同一笔记只保留分数最高的 chunk）
        by_note: dict = {}
        for h in kw_hits + vec_hits:
            nid = h["note_id"]
            if nid not in by_note or h["score"] > by_note[nid]["score"]:
                by_note[nid] = h
        retrieved = sorted(by_note.values(), key=lambda x: -x["score"])[:req.top_k]
        # 清理调试字段
        for h in retrieved:
            h.pop("_matched", None)

        logger.info(f"🔍 检索到 {len(retrieved)} 条相关笔记（关键词 {len(kw_hits)} + 向量 {len(vec_hits)}）")

        # 2. 拼 prompt（含历史 + 检索）
        system, user_msg = build_rag_prompt(req.question, retrieved, history=history)

        # 3. 发送 start 事件（含引用 + demo 标记）
        yield f"data: {json.dumps({'type': 'start', 'references': retrieved, 'is_demo': llm.is_demo}, ensure_ascii=False)}\n\n"

        # 4. 存用户问题到对话历史
        # (v1 简化：存到 DB)
        # 这里先跳过，stream 完成后存

        # 5. 流式生成
        full_answer = ""
        for delta in llm.chat_stream(system, user_msg):
            full_answer += delta
            yield f"data: {json.dumps({'type': 'delta', 'content': delta}, ensure_ascii=False)}\n\n"

        # 6. done
        yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"

        # 7. 异步存对话历史（fire-and-forget）
        import asyncio
        async def _save_history():
            from app.core.database import SessionLocal
            db = SessionLocal()
            try:
                db.add(Conversation(user_id=user.id, role="user", content=req.question))
                db.add(Conversation(
                    user_id=user.id, role="assistant", content=full_answer,
                    referenced_notes=json.dumps([r["note_id"] for r in retrieved]),
                ))
                db.commit()
            finally:
                db.close()
        asyncio.create_task(_save_history())

    except Exception as e:
        logger.exception(f"chat stream 失败: {e}")
        yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
):
    """流式问答（SSE）"""
    return StreamingResponse(
        _stream_chat(current_user, req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/history")
def chat_history(
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取对话历史（按时间倒序）"""
    items = (
        db.query(Conversation)
        .filter(Conversation.user_id == current_user.id)
        .order_by(Conversation.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "id": c.id,
                "role": c.role,
                "content": c.content,
                "referenced_notes": json.loads(c.referenced_notes) if c.referenced_notes else [],
                "created_at": c.created_at.isoformat(),
            }
            for c in items
        ]
    }
