"""
向量检索测试
"""
import sys
import os
import shutil
import pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_BASE = os.path.join(os.path.dirname(__file__), "_test_retrieval_tmp")
_ctr = 0


@pytest.fixture(autouse=True)
def cleanup():
    """每次测试前清理上次残留的 ChromaDB 持久化数据"""
    global _ctr
    _ctr = 0
    if os.path.exists(TEST_BASE):
        shutil.rmtree(TEST_BASE, ignore_errors=True)
    yield
    if os.path.exists(TEST_BASE):
        shutil.rmtree(TEST_BASE, ignore_errors=True)


def tmp():
    """每次测试用独立子目录（避免 ChromaDB 文件锁冲突）"""
    global _ctr
    _ctr += 1
    d = os.path.join(TEST_BASE, str(_ctr))
    os.makedirs(d, exist_ok=True)
    return d


def test_vector_store_init():
    print("=" * 50)
    print("测试: VectorStore 初始化")
    from src.retrieval import VectorStore

    store = VectorStore(tmp())
    assert store is not None
    col = store.get_or_create_collection("test")
    assert col.name == "test"
    assert "test" in store.list_collections()
    print("✅ VectorStore 初始化成功")


def test_add_and_query():
    print("=" * 50)
    print("测试: VectorStore 添加 + 查询")
    from src.retrieval import VectorStore

    store = VectorStore(tmp())
    docs = [
        "沈安在破庙醒来，发现自己的记忆又被替换了。",
        "遗忘石是一种可以记录记忆修改的石头。",
        "赵肃是前一朝的天听密探统领。",
    ]
    meta = [{"chapter": 1}, {"chapter": 0}, {"chapter": 0}]
    ids = store.add("test_col", docs, meta)
    assert len(ids) == 3 and store.count("test_col") == 3
    r = store.query("test_col", "记忆被替换", n_results=2)
    assert r["documents"][0] and "沈安" in r["documents"][0][0]
    print(f"✅ 添加 3 条，查询命中: {r['documents'][0][0][:40]}...")


def test_document_indexer():
    print("=" * 50)
    print("测试: DocumentIndexer")
    from src.retrieval import VectorStore, DocumentIndexer

    t = tmp()
    os.makedirs(os.path.join(t, "chapters"), exist_ok=True)

    open(os.path.join(t, "story_frame.md"), "w", encoding="utf-8").write(
        "故事：沈安每七天记忆被替换。天听密探组织覆灭。"
    )
    open(os.path.join(t, "roles.md"), "w", encoding="utf-8").write(
        "---ROLE---\nname: 沈安\n前朝密探，记忆被替换。\n---CONTENT---\n"
        "沈安每七天醒来都是一个新人，靠纸条追踪自己。"
    )
    open(os.path.join(t, "book_rules.md"), "w", encoding="utf-8").write("")
    open(os.path.join(t, "chapter_summaries.md"), "w", encoding="utf-8").write(
        "1. 沈安在破庙醒来，发现自己的记忆被替换了，决定查明真相离开破庙。\n"
        "2. 沈安在废弃村落遇到阿沅，对方手腕上的刀疤与他的刀法一致。\n"
    )
    open(os.path.join(t, "chapters", "chapter_0001.md"), "w", encoding="utf-8").write(
        "沈安醒来的时候，嘴里有一股铁锈味。他躺在冰冷的石地面上。"
        "柱子上刻着一行字：兄弟，你叫沈安。今天是十月初七。别慌。"
    )

    store = VectorStore(t)
    counts = DocumentIndexer(store).index_project(t)

    print(f"  foundations: {counts.get('foundations',0)}")
    print(f"  chapters: {counts.get('chapters',0)}")
    print(f"  hooks: {counts.get('hooks',0)}")

    assert counts["foundations"] >= 1
    assert counts["chapters"] >= 2, f"chapters={counts['chapters']}"
    print("✅ 索引完成")

    # 验证搜索
    r = store.query("chapters", "铁锈味 破庙 沈安", n_results=2)
    assert r["documents"][0]
    assert any(w in r["documents"][0][0] for w in ["铁锈味", "破庙", "沈安"])
    print(f"✅ 语义搜索命中: {r['documents'][0][0][:50]}...")


def test_retriever_and_context():
    print("=" * 50)
    print("测试: SemanticRetriever + ContextBuilder")
    from src.retrieval import VectorStore, DocumentIndexer, SemanticRetriever
    from src.utils.context_builder import ContextBuilder

    t = tmp()
    os.makedirs(os.path.join(t, "chapters"), exist_ok=True)

    open(os.path.join(t, "story_frame.md"), "w", encoding="utf-8").write(
        "架空古代，天听密探覆灭后，前密探沈安记忆每七天替换。"
    )
    open(os.path.join(t, "roles.md"), "w", encoding="utf-8").write(
        "---ROLE---\ntier: major\nname: 沈安\n---CONTENT---\n前朝密探。\n\n"
        "---ROLE---\ntier: major\nname: 阿沅\n---CONTENT---\n同伴，右手腕有刀疤。"
    )
    open(os.path.join(t, "book_rules.md"), "w", encoding="utf-8").write("")
    open(os.path.join(t, "volume_map.md"), "w", encoding="utf-8").write(
        "第一卷：觉醒\n第二卷：西门之内"
    )
    open(os.path.join(t, "chapter_summaries.md"), "w", encoding="utf-8").write(
        "1. 沈安在破庙醒来发现记忆被替换，决定查明真相离开破庙。\n"
        "2. 沈安在废弃村落遇到了阿沅得知了自己天听密探的身份。\n"
        "3. 沈安进入西门在城中发现了天听阁废弃入口开始探寻。\n"
    )
    open(os.path.join(t, "pending_hooks.md"), "w", encoding="utf-8").write(
        "[startChapter=1] 遗忘石上有未闭合的圆——记忆操作记录。"
    )

    store = VectorStore(t)
    DocumentIndexer(store).index_project(t)

    # 检索
    retriever = SemanticRetriever(store)
    query = retriever.build_query(4, {
        "user_guidance": "沈安进入天听阁地下废墟",
        "roles": "沈安 阿沅",
    })
    results = retriever.retrieve_for_chapter(4, query, n_results=3)
    assert results.total_found >= 1, f"total_found={results.total_found}"
    print(f"✅ 检索到 {results.total_found} 条结果")

    formatted = results.format_for_prompt()
    assert "语义相关历史" in formatted
    print(f"✅ 格式化: {len(formatted)} 字")

    # ContextBuilder
    ctx = ContextBuilder(t).build(4, "沈安进入天听阁废墟")
    assert ctx.semantic_hits and "语义相关历史" in ctx.semantic_hits
    full = ctx.build_prompt_context()
    assert "语义相关" in full
    print(f"✅ 集成成功，上下文: {len(full)} 字")


def main():
    print("\n🧪 向量检索测试\n")
    # 清理上次残留
    if os.path.exists(TEST_BASE):
        shutil.rmtree(TEST_BASE, ignore_errors=True)
    tests = [
        test_vector_store_init,
        test_add_and_query,
        test_document_indexer,
        test_retriever_and_context,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"\n❌ {t.__name__}: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    print(f"\n{'='*50}\n结果: {passed} 通过, {failed} 失败\n{'='*50}")
    return failed == 0


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
