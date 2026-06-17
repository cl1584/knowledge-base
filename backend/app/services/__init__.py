"""RAG 核心：embedding + 向量检索 + DeepSeek 问答"""
import asyncio
import json
from pathlib import Path
from typing import List, Optional
from loguru import logger

from app.core.config import settings

# 可选依赖：没装也能跑基础 API（仅日志告警）
try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("⚠️ chromadb 未安装，将用 numpy 兜底方案（pip install chromadb 升级）")

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False
    logger.warning("⚠️ openai 未安装，DeepSeek 对话不可用（pip install openai 启用）")

import numpy as np  # 兜底方案必备


# ========== Embedding ==========
class EmbeddingService:
    """调用 DashScope text-embedding-v2（或本地模型）"""

    def __init__(self):
        self.api_key = settings.dashscope_api_key
        self.model = settings.embedding_model
        self.client = None
        if self.api_key and HAS_OPENAI:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            )

    def embed(self, texts: List[str]) -> List[List[float]]:
        """同步 embed 一批文本"""
        if not self.client:
            # 假数据：随机向量（仅 dev 模式 / 无 API key）
            import random
            random.seed(42)
            return [[random.gauss(0, 1) for _ in range(settings.embedding_dim)] for _ in texts]

        results: List[List[float]] = []
        for i in range(0, len(texts), 10):
            batch = texts[i:i + 10]
            resp = self.client.embeddings.create(model=self.model, input=batch)
            for d in resp.data:
                results.append(d.embedding)
        return results

    async def aembed(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.to_thread(self.embed, texts)


# ========== Vector Store ==========
class NumpyVectorStore:
    """numpy 兜底方案：每个用户一个 .npz 文件 + 内存缓存"""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)
        self._cache: dict[int, dict] = {}  # user_id -> data

    def _path(self, user_id: int) -> Path:
        return self.base_path / f"user_{user_id}.npz"

    def _load(self, user_id: int) -> dict:
        """加载用户的全部向量（带内存缓存）"""
        if user_id in self._cache:
            return self._cache[user_id]
        p = self._path(user_id)
        if not p.exists():
            data = {"ids": [], "vectors": np.zeros((0, settings.embedding_dim), dtype=np.float32),
                    "documents": [], "metadatas": []}
        else:
            with np.load(p, allow_pickle=True) as f:
                data = {
                    "ids": f["ids"].tolist(),
                    "vectors": f["vectors"],
                    "documents": f["documents"].tolist(),
                    "metadatas": f["metadatas"].tolist(),
                }
        self._cache[user_id] = data
        return data

    def _save(self, user_id: int, data: dict):
        self._cache[user_id] = data  # 同步更新缓存
        p = self._path(user_id)
        np.savez(p,
                 ids=np.array(data["ids"]),
                 vectors=data["vectors"].astype(np.float32),
                 documents=np.array(data["documents"], dtype=object),
                 metadatas=np.array(data["metadatas"], dtype=object))

    def invalidate(self, user_id: int):
        """清除某用户的缓存（用于外部修改文件后）"""
        self._cache.pop(user_id, None)

    def add(self, user_id: int, ids: List[str], vectors: np.ndarray, documents: List[str], metadatas: List[dict]):
        data = self._load(user_id)
        # 移除同 note_id 的旧 chunk
        new_note_ids = {m["note_id"] for m in metadatas}
        keep_mask = [m["note_id"] not in new_note_ids for m in data["metadatas"]]
        data["ids"] = [i for i, k in zip(data["ids"], keep_mask) if k]
        data["vectors"] = data["vectors"][keep_mask] if data["vectors"].size > 0 else data["vectors"]
        data["documents"] = [d for d, k in zip(data["documents"], keep_mask) if k]
        data["metadatas"] = [m for m, k in zip(data["metadatas"], keep_mask) if k]
        # 追加新的
        if vectors.size > 0:
            data["ids"].extend(ids)
            data["vectors"] = np.vstack([data["vectors"], vectors]) if data["vectors"].size else vectors
            data["documents"].extend(documents)
            data["metadatas"].extend(metadatas)
        self._save(user_id, data)

    def delete_note(self, user_id: int, note_id: int):
        data = self._load(user_id)
        keep_mask = [m["note_id"] != note_id for m in data["metadatas"]]
        if not any(keep_mask):  # 全部要删
            p = self._path(user_id)
            if p.exists(): p.unlink()
            return
        data["ids"] = [i for i, k in zip(data["ids"], keep_mask) if k]
        data["vectors"] = data["vectors"][keep_mask] if data["vectors"].size else data["vectors"]
        data["documents"] = [d for d, k in zip(data["documents"], keep_mask) if k]
        data["metadatas"] = [m for m, k in zip(data["metadatas"], keep_mask) if k]
        self._save(user_id, data)

    def search(self, user_id: int, query_vec: List[float], top_k: int = 8) -> List[dict]:
        data = self._load(user_id)
        if data["vectors"].shape[0] == 0:
            return []
        # 余弦相似度
        q = np.array(query_vec, dtype=np.float32)
        q_norm = q / (np.linalg.norm(q) + 1e-8)
        v_norms = data["vectors"] / (np.linalg.norm(data["vectors"], axis=1, keepdims=True) + 1e-8)
        sims = (v_norms @ q_norm).astype(np.float32)
        top_idx = np.argsort(-sims)[:top_k]
        results = []
        for i in top_idx:
            results.append({
                "note_id": int(data["metadatas"][i]["note_id"]),
                "title": str(data["metadatas"][i].get("title", "")),
                "content": str(data["documents"][i]),
                "score": float(sims[i]),
            })
        return results

    def count(self, user_id: int) -> int:
        return len(self._load(user_id)["ids"])


class VectorStore:
    """统一接口：优先 chromadb，否则 numpy 兜底"""

    def __init__(self):
        self.embedding = EmbeddingService()
        self.chroma = None
        self.numpy_store = None

        if HAS_CHROMADB:
            try:
                self.chroma = chromadb.PersistentClient(
                    path=str(settings.chroma_path),
                    settings=ChromaSettings(anonymized_telemetry=False),
                )
            except Exception as e:
                logger.warning(f"⚠️ chromadb 初始化失败：{e}")
                self.chroma = None

        if self.chroma is None:
            # 用 numpy 兜底
            np_path = settings.chroma_path / "numpy"
            self.numpy_store = NumpyVectorStore(np_path)
            logger.info(f"📦 使用 numpy 兜底向量库：{np_path}")

    def _collection_name(self, user_id: int) -> str:
        return f"user_{user_id}_notes"

    def _get_collection(self, user_id: int):
        if not self.chroma:
            return None
        return self.chroma.get_or_create_collection(
            name=self._collection_name(user_id),
            metadata={"hnsw:space": "cosine"},
        )

    def _chunk_text(self, text: str) -> List[str]:
        if not text.strip():
            return []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        chunks: List[str] = []
        for p in paragraphs:
            if len(p) <= settings.chunk_size:
                chunks.append(p)
            else:
                sentences = p.replace("。", "。\n").replace("！", "！\n").replace("？", "？\n").split("\n")
                cur = ""
                for s in sentences:
                    if len(cur) + len(s) > settings.chunk_size and cur:
                        chunks.append(cur.strip())
                        cur = s
                    else:
                        cur += s
                if cur.strip():
                    chunks.append(cur.strip())
        return chunks

    def index_note(self, note_id: int, user_id: int, title: str, content: str):
        chunks = self._chunk_text(content or title)
        if not chunks:
            return
        embeddings = self.embedding.embed(chunks)
        embeddings_np = np.array(embeddings, dtype=np.float32)
        ids = [f"n{note_id}_c{i}" for i in range(len(chunks))]
        metadatas = [{"note_id": note_id, "chunk_index": i, "title": title} for i in range(len(chunks))]

        if self.chroma:
            col = self._get_collection(user_id)
            if col:
                # 先删旧的
                existing = col.get(where={"note_id": note_id})
                if existing and existing["ids"]:
                    col.delete(ids=existing["ids"])
                col.add(ids=ids, embeddings=embeddings, documents=chunks, metadatas=metadatas)
        else:
            self.numpy_store.add(user_id, ids, embeddings_np, chunks, metadatas)
        logger.info(f"📥 indexed note {note_id}: {len(chunks)} chunks")

    def delete_note(self, note_id: int, user_id: int):
        if self.chroma:
            col = self._get_collection(user_id)
            if col:
                existing = col.get(where={"note_id": note_id})
                if existing and existing["ids"]:
                    col.delete(ids=existing["ids"])
        else:
            self.numpy_store.delete_note(user_id, note_id)

    def search(self, user_id: int, query: str, top_k: int = 8) -> List[dict]:
        q_emb = self.embedding.embed([query])[0]
        if self.chroma:
            col = self._get_collection(user_id)
            if not col or col.count() == 0:
                return []
            results = col.query(query_embeddings=[q_emb], n_results=min(top_k, col.count()))
            hits = []
            if results and results["documents"]:
                for i, doc in enumerate(results["documents"][0]):
                    meta = results["metadatas"][0][i] if results.get("metadatas") else {}
                    dist = results["distances"][0][i] if results.get("distances") else 0
                    hits.append({
                        "note_id": meta.get("note_id"),
                        "title": meta.get("title", ""),
                        "content": doc,
                        "score": 1 - dist,
                    })
            return hits
        else:
            return self.numpy_store.search(user_id, q_emb, top_k)

    def search_by_keywords(self, user_id: int, query: str, top_k: int = 8) -> List[dict]:
        """关键词检索：BM25-like 打分，不依赖 embedding
        适用于没装 DashScope / 没配 embedding 的情况
        """
        from app.core.database import SessionLocal
        from app.models import Note
        from sqlalchemy import or_

        # 简单中文分词（不依赖 jieba）
        import re
        # 拆出中文字符 + 英文单词
        def tokenize(text: str) -> set:
            if not text:
                return set()
            tokens = set()
            # 中文每个字单独算 token（粗粒度，但够用）
            for ch in re.findall(r'[一-鿿]', text):
                tokens.add(ch)
            # 英文/数字按词
            for w in re.findall(r'[a-zA-Z0-9]+', text.lower()):
                tokens.add(w)
            return tokens

        q_tokens = tokenize(query)
        if not q_tokens:
            return []

        db = SessionLocal()
        try:
            # 拿所有未删笔记
            notes = db.query(Note).filter(
                Note.user_id == user_id,
                Note.deleted_at.is_(None),
                Note.is_archived == False,
            ).all()
        finally:
            db.close()

        scored = []
        for note in notes:
            title_tokens = tokenize(note.title or "")
            content_tokens = tokenize(note.content or "")
            all_tokens = title_tokens | content_tokens

            if not all_tokens:
                continue

            # 计算 overlap
            overlap = q_tokens & all_tokens
            if not overlap:
                continue

            # 标题命中加权
            title_hit = len(q_tokens & title_tokens)
            content_hit = len(overlap) - title_hit

            # 简单 BM25-like 分数
            # - 标题命中权重高（2x）
            # - 覆盖率（命中数 / 查询数）
            coverage = len(overlap) / len(q_tokens)
            score = (title_hit * 2.0 + content_hit * 1.0) * coverage

            # 把笔记切 chunk（用整个笔记作为一个 chunk）
            scored.append({
                "note_id": note.id,
                "title": note.title or "未命名笔记",
                "content": (note.content or "")[:800],   # 取前 800 字
                "score": score,
                "_matched": list(overlap)[:5],  # 调试用
            })

        scored.sort(key=lambda x: -x["score"])
        return scored[:top_k]


# ========== LLM (DeepSeek / OpenAI 兼容) ==========
class LLMService:
    """LLM 对话，支持流式；每次按用户配置创建实例"""

    def __init__(self, api_key: str = "", base_url: str = "", model: str = ""):
        # 参数 > 用户配置 > 系统默认（settings）
        self.api_key = api_key or settings.deepseek_api_key
        self.base_url = base_url or settings.deepseek_base_url
        self.model = model or settings.deepseek_model
        self.client = None
        if self.api_key and HAS_OPENAI:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
        self.is_demo = self.client is None

    def chat_stream(self, system_prompt: str, user_message: str):
        """生成器：流式返回 token"""
        if not self.client:
            yield "（演示模式：请在设置中配置 API Key 并安装 openai 库）"
            return
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            stream=True,
            temperature=0.7,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                yield delta


# ========== Singleton (VectorStore 保留单例) ==========
_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_llm_for_user(user) -> LLMService:
    """为用户创建 LLMService（用用户配置，缺失则走系统默认）"""
    if user:
        return LLMService(
            api_key=user.ai_api_key or "",
            base_url=user.ai_base_url or "",
            model=user.ai_model or "",
        )
    return LLMService()
