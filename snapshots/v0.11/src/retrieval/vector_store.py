"""
VectorStore — ChromaDB 封装

职责：
- 管理 ChromaDB 客户端和 collection
- 提供基础的 embed / add / query 接口
- 使用本地 sentence-transformers 嵌入模型，无需 API 调用
"""

import os
import logging
from typing import List, Optional, Dict, Any
import uuid

# 纯离线：禁止 huggingface_hub 联网检查
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

log = logging.getLogger(__name__)

# 使用轻量中文嵌入模型
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


class VectorStore:
    """ChromaDB 向量存储"""

    def __init__(self, project_dir: str, model_name: str = MODEL_NAME):
        """
        初始化向量存储。

        Args:
            project_dir: 项目目录（ChromaDB 数据会存在 project_dir/.chroma/）
            model_name: sentence-transformers 模型名
        """
        self.project_dir = project_dir
        persist_dir = os.path.join(project_dir, ".chroma")

        # 嵌入函数（local_files_only=True 禁止联网检查，纯离线加载本地缓存模型）
        self._embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=model_name,
            device="cpu",
            local_files_only=True,
        )

        # 客户端
        self._client = chromadb.PersistentClient(
            path=persist_dir,
            settings=Settings(anonymized_telemetry=False),
        )

        log.info(f"[VectorStore] 初始化完成 (model={model_name}, dir={persist_dir})")

    # ── Collection 管理 ──────────────────────────────────────────────

    def get_or_create_collection(self, name: str):
        """获取或创建 collection"""
        return self._client.get_or_create_collection(
            name=name,
            embedding_function=self._embed_fn,
            metadata={"hnsw:space": "cosine"},
        )

    def list_collections(self) -> List[str]:
        """列出所有 collection"""
        return [c.name for c in self._client.list_collections()]

    def delete_collection(self, name: str) -> None:
        """删除 collection"""
        try:
            self._client.delete_collection(name)
            log.info(f"[VectorStore] 已删除 collection: {name}")
        except Exception:
            pass

    # ── 基本操作 ─────────────────────────────────────────────────────

    def add(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """
        添加文档到向量存储。

        Args:
            collection_name: collection 名称
            documents: 文档文本列表
            metadatas: 元数据列表（source, chapter, type 等）
            ids: 文档 ID 列表（不提供则自动生成）

        Returns:
            添加的文档 ID 列表
        """
        col = self.get_or_create_collection(collection_name)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        col.add(documents=documents, metadatas=metadatas or [{}] * len(documents), ids=ids)
        log.info(f"[VectorStore] 添加 {len(documents)} 条文档到 '{collection_name}'")
        return ids

    def query(
        self,
        collection_name: str,
        query_text: str,
        n_results: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        语义搜索。

        Args:
            collection_name: collection 名称
            query_text: 查询文本
            n_results: 返回结果数
            where: ChromaDB 过滤条件

        Returns:
            {
                "documents": [[str, ...]],
                "metadatas": [[dict, ...]],
                "distances": [[float, ...]],
                "ids": [[str, ...]],
            }
        """
        try:
            col = self._client.get_collection(
                name=collection_name,
                embedding_function=self._embed_fn,
            )
        except Exception:
            return {"documents": [[]], "metadatas": [[]], "distances": [[]], "ids": [[]]}

        results = col.query(
            query_texts=[query_text],
            n_results=n_results,
            where=where,
        )
        return results

    def count(self, collection_name: str) -> int:
        """返回 collection 中的文档数"""
        try:
            col = self._client.get_collection(
                name=collection_name,
                embedding_function=self._embed_fn,
            )
            return col.count()
        except Exception:
            return 0

    def clear(self, collection_name: str) -> None:
        """清空 collection 并重建"""
        self.delete_collection(collection_name)
        self.get_or_create_collection(collection_name)
        log.info(f"[VectorStore] 已重置 collection: {collection_name}")

    def upsert(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> List[str]:
        """更新或插入文档（按 ID 去重）"""
        col = self.get_or_create_collection(collection_name)
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]
        col.upsert(documents=documents, metadatas=metadatas or [{}] * len(documents), ids=ids)
        return ids
