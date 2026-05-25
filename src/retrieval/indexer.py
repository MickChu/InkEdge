"""
DocumentIndexer — 文档索引器

将 foundation 文件和章节目录索引到 ChromaDB，支持增量更新。
"""

import os
import re
import logging
from typing import List, Dict, Optional

from src.retrieval.vector_store import VectorStore
from src.utils.file_io import read_file

log = logging.getLogger(__name__)

# Collection 名称
COL_CHAPTERS = "chapters"            # 章节摘要
COL_FOUNDATIONS = "foundations"      # story_frame, roles, book_rules
COL_HOOKS = "hooks"                  # 活跃伏笔

# 文本分块：每段 500 字左右，适合语义检索
CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


class DocumentIndexer:
    """索引器：将项目文档索引到向量存储"""

    def __init__(self, store: VectorStore):
        self.store = store

    # ── 全量索引 ─────────────────────────────────────────────────────

    def index_project(self, project_dir: str) -> Dict[str, int]:
        """
        对项目进行全量索引。
        返回各 collection 的文档数。
        """
        counts = {}

        # 1. 索引 foundation 文件
        counts[COL_FOUNDATIONS] = self._index_foundations(project_dir)

        # 2. 索引章节摘要
        counts[COL_CHAPTERS] = self._index_chapters(project_dir)

        # 3. 索引伏笔
        counts[COL_HOOKS] = self._index_hooks(project_dir)

        log.info(f"[Indexer] 全量索引完成: {counts}")
        return counts

    def _index_foundations(self, project_dir: str) -> int:
        """索引 foundation 文件"""
        self.store.clear(COL_FOUNDATIONS)

        documents = []
        metadatas = []

        files = {
            "story_frame.md": "base",
            "roles.md": "base",
            "book_rules.md": "base",
        }

        for filename, doc_type in files.items():
            content = read_file(os.path.join(project_dir, filename), default="")
            if not content:
                continue

            # 分块索引
            chunks = self._chunk_text(content)
            for i, chunk in enumerate(chunks):
                doc_id = f"{filename.replace('.md','')}_{i}"
                documents.append(chunk)
                metadatas.append({
                    "source": filename,
                    "type": doc_type,
                    "chunk": i,
                    "chapter": 0,
                })

        if documents:
            self.store.add(COL_FOUNDATIONS, documents, metadatas)
        return len(documents)

    def _index_chapters(self, project_dir: str) -> int:
        """索引章节摘要"""
        self.store.clear(COL_CHAPTERS)

        # 读取章节摘要文件
        summary_path = os.path.join(project_dir, "chapter_summaries.md")
        summary_text = read_file(summary_path, default="")
        if not summary_text:
            return 0

        # 也索引已保存的章节正文
        chapters_dir = os.path.join(project_dir, "chapters")
        documents = []
        metadatas = []

        # 方式1：从 chapter_summaries.md 按行索引
        for line in summary_text.strip().split("\n"):
            line = line.strip()
            if not line:
                continue

            # 解析 "N. 内容"
            match = re.match(r"(\d+)\.\s*(.+)", line)
            if match:
                chapter_num = int(match.group(1))
                summary = match.group(2).strip()
                if len(summary) > 20:  # 至少 20 字才索引（可搜索）
                    doc_id = f"summary_{chapter_num:04d}"
                    documents.append(summary)
                    metadatas.append({
                        "source": "chapter_summaries.md",
                        "type": "summary",
                        "chapter": chapter_num,
                    })

        # 方式2：从章节正文文件中提取
        if os.path.isdir(chapters_dir):
            for fname in sorted(os.listdir(chapters_dir)):
                if not fname.startswith("chapter_") or not fname.endswith(".md"):
                    continue
                ch_num = int(fname.replace("chapter_", "").replace(".md", ""))
                content = read_file(os.path.join(chapters_dir, fname), default="")
                if not content:
                    continue

                # 只索引每章的前 800 字 + 后 200 字（核心内容区）
                head = content[:800]
                tail = content[-200:] if len(content) > 200 else ""

                if len(head) > 100:
                    doc_id = f"chapter_{ch_num:04d}_head"
                    documents.append(head)
                    metadatas.append({
                        "source": fname,
                        "type": "chapter_text",
                        "chapter": ch_num,
                    })

                if len(tail) > 50:
                    doc_id = f"chapter_{ch_num:04d}_tail"
                    documents.append(tail)
                    metadatas.append({
                        "source": fname,
                        "type": "chapter_text",
                        "chapter": ch_num,
                    })

        if documents:
            self.store.add(COL_CHAPTERS, documents, metadatas)
        return len(documents)

    def _index_hooks(self, project_dir: str) -> int:
        """索引活跃伏笔"""
        self.store.clear(COL_HOOKS)

        hooks_path = os.path.join(project_dir, "pending_hooks.md")
        content = read_file(hooks_path, default="")
        if not content:
            return 0

        documents = []
        metadatas = []
        chapters = set()

        # 解析钩子：查找 [startChapter=N] 模式
        hook_pattern = re.compile(
            r'\[startChapter[=:]\s*(\d+)\](.*?)(?=\[startChapter|\Z)',
            re.DOTALL,
        )
        for match in hook_pattern.finditer(content):
            ch_num = int(match.group(1))
            hook_text = match.group(2).strip()
            if len(hook_text) > 30:
                doc_id = f"hook_{ch_num:04d}_{len(metadatas)}"
                documents.append(hook_text)
                metadatas.append({
                    "source": "pending_hooks.md",
                    "type": "hook",
                    "chapter": ch_num,
                })
                chapters.add(ch_num)

        # 如果没有匹配到 [startChapter]，整段索引
        if not documents and len(content) > 50:
            doc_id = "hooks_all"
            documents.append(content[:1000])
            metadatas.append({
                "source": "pending_hooks.md",
                "type": "hook",
                "chapter": 0,
            })

        if documents:
            self.store.add(COL_HOOKS, documents, metadatas)
        return len(documents)

    # ── 增量索引 ─────────────────────────────────────────────────────

    def index_new_chapter(self, project_dir: str, chapter_number: int, summary: str) -> int:
        """
        新章节写完后增量索引。
        只索引这一章的摘要到向量存储（不重建全库）。
        """
        if len(summary) < 20:
            return 0

        doc_id = f"summary_{chapter_number:04d}"
        meta = {
            "source": "chapter_summaries.md",
            "type": "summary",
            "chapter": chapter_number,
        }
        self.store.upsert(COL_CHAPTERS, [summary], [meta], [doc_id])
        log.info(f"[Indexer] 新增索引 第 {chapter_number} 章摘要")
        return 1

    # ── 辅助方法 ─────────────────────────────────────────────────────

    def _chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE,
                    overlap: int = CHUNK_OVERLAP) -> List[str]:
        """将长文本按段落边界分块"""
        if len(text) <= chunk_size:
            return [text]

        chunks = []
        paragraphs = text.split("\n\n")

        current = ""
        for para in paragraphs:
            if len(current) + len(para) > chunk_size and current:
                chunks.append(current.strip())
                # 保留最后 overlap 字符作为重叠
                if overlap > 0 and len(current) > overlap:
                    current = current[-overlap:]
                else:
                    current = ""
            current += "\n\n" + para if current else para

        if current.strip():
            chunks.append(current.strip())

        return chunks


# 便捷函数
def index_project(project_dir: str, store: Optional[VectorStore] = None) -> Dict[str, int]:
    """索引整个项目"""
    if store is None:
        store = VectorStore(project_dir)
    indexer = DocumentIndexer(store)
    return indexer.index_project(project_dir)
