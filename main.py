#!/usr/bin/env python3
"""
InkEdge — Python 统一小说生成框架

融合 inkOS 多Agent架构 + AI_NovelGenerator 向量检索/雪花法/状态追踪

用法:
    # 创建新书（Architect → 生成 foundation）
    python main.py new --name "我的小说" --topic "一个AI在末世觉醒的故事" --genre 科幻 --chapters 60

    # 续写章节（Writer → 智能生成）
    python main.py write --name "我的小说" --chapter 5

    # 批量写稿
    python main.py write --name "我的小说" --from 3 --to 10

    # 一致性检查
    python main.py check --name "我的小说" --chapter 10

    # 查看项目状态
    python main.py status --name "我的小说"

    # 启动 Studio GUI
    python main.py studio
"""

import argparse
import asyncio
import logging
import sys

# Windows GBK console 不支持 emoji，强制 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger("inkedge")


def get_project_dir(name: str) -> str:
    """获取项目目录"""
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "projects", name)


async def cmd_templates(args):
    """列出可用模板"""
    from src.prompts import get_template_registry
    registry = get_template_registry()
    templates = registry.list_with_info()

    print(f"\n📚 可用的写作方法论模板 ({len(templates)} 套)\n")
    for t in templates:
        print(f"  {t['name']:20s} — {t['display_name']}")
        print(f"  {'':20s}   {t['description']}")
        print(f"  {'':20s}   版本: {t['version']} | 步骤: {t['steps']} | 适用: {', '.join(t['genres'])}")
        print()


def _load_source_materials(source_dir: str) -> dict:
    """读取目录下的 .md/.txt 文件，返回 {文件名: 内容} 字典
    
    排除：二进制文件、子目录（如 .inkos/、小说内容/）、临时文件。
    """
    import os
    materials = {}
    if not os.path.isdir(source_dir):
        return materials

    for fname in sorted(os.listdir(source_dir)):
        fpath = os.path.join(source_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not fname.lower().endswith(('.md', '.txt')):
            continue
        # 跳过临时/提取脚本
        if fname.startswith(('.', '_')):
            continue
        skip_names = {'convert_to_md.py', 'extract_chapters.py', 'extract_docx.py',
                      'retry_failed.py', 'rewrite_jinyong.py', 'test_rewrite.py'}
        if fname in skip_names:
            continue

        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            if content:
                # 文件名去后缀作为 key
                key = fname.rsplit('.', 1)[0]
                materials[key] = content
        except (UnicodeDecodeError, PermissionError):
            pass  # 跳过二进制或无权文件

    return materials


async def cmd_new(args):
    """创建新书"""
    import os
    from src.core.base_agent import AgentContext
    from src.core.orchestrator import Orchestrator, PipelineStep
    from src.agents.architect import ArchitectAgent

    template_name = getattr(args, 'template', 'snowflake')

    project_dir = get_project_dir(args.name)
    log.info(f"📖 创建新书: {args.name}")
    log.info(f"   主题: {args.topic}")
    log.info(f"   类型: {args.genre}")
    log.info(f"   目标: {args.chapters}章 × ~{args.words}字/章")
    log.info(f"   路径: {project_dir}")

    extra = {
        "genre": args.genre,
        "num_chapters": args.chapters,
        "word_number": args.words,
        "template_name": template_name,
    }

    # --from-dir: 加载已有材料目录
    from_dir = getattr(args, 'from_dir', None)
    if from_dir:
        materials = _load_source_materials(from_dir)
        if materials:
            extra["source_materials"] = materials
            log.info(f"   📂 材料目录: {from_dir}")
            log.info(f"   加载 {len(materials)} 个文件 ({sum(len(v) for v in materials.values())} 字)")
            for name in materials:
                log.info(f"      • {name} ({len(materials[name])} 字)")
        else:
            log.warning(f"   ⚠️ {from_dir} 中未找到 .md/.txt 文件，将使用自由创作模式")

    context = AgentContext(
        project_dir=project_dir,
        user_guidance=args.topic,
        extra=extra,
    )

    # ═══ Wizard 交互模式 ═══
    if getattr(args, 'wizard', False):
        architect = ArchitectAgent(template_name="snowflake")
        state = architect.wizard_init(context)
        steps = state["steps"]

        print(f"\n🧙 交互式建书模式 — 共 {len(steps)} 步")
        print(f"   每步生成后你可以：")
        print(f"   [Enter] 确认继续  |  retry 重新生成  |  edit <修改意见>")

        for i, step in enumerate(steps):
            feedback = state["step_feedback"].get(i, "")
            while True:
                output = await architect.wizard_run_step(state, i, retry=bool(feedback))

                print(f"\n{'─'*60}")
                print(f"📋 第 {i+1}/{len(steps)} 步: {step.name}")
                print(f"{'─'*60}")
                print(output)
                print(f"{'─'*60}")

                # 清掉本次反馈（已使用）
                state["step_feedback"][i] = ""

                action = input("\n[Enter] 继续 | retry | edit <意见>: ").strip()
                if action == "":
                    break  # 确认，进入下一步
                elif action == "retry":
                    log.info(f"   🔄 重新生成第 {i+1} 步...")
                    continue
                elif action.startswith("edit "):
                    fb = action[5:].strip()
                    architect.wizard_set_feedback(state, i, fb)
                    log.info(f"   ✏️ 已记录修改意见，重新生成...")
                    continue
                else:
                    print("   ⚠️ 未知命令。可用: [Enter] / retry / edit <意见>")
                    # 不清 feedback，下次重试时继续用
                    state["step_feedback"][i] = feedback
                    continue

        architect.wizard_finalize(state)
        log.info(f"✅ 建书完成! 设定文件已保存到 {project_dir}")
        return

    # ═══ 原有逻辑（非 wizard） ═══
    log.info(f"   模板: {template_name}")
    if not from_dir:
        log.info(f"   ✨ 自由创作模式（仅基于主题描述）")

    # --model 覆盖
    model = getattr(args, 'model', None)
    if model:
        from src.utils.config import config as cfg
        cfg.set("model_name", model)
        log.info(f"   模型: {model}")

    orchestrator = Orchestrator(project_dir)
    architect = ArchitectAgent(template_name=template_name)
    steps = [PipelineStep(agent=architect, required=True)]

    result = await orchestrator.run_sequential(steps, context)
    if result.success:
        log.info(f"✅ 建书完成! 设定文件已保存到 {project_dir}")
    else:
        log.error(f"❌ 建书失败: {result.error}")
        sys.exit(1)


async def cmd_write(args):
    """续写章节"""
    import os
    from src.core.base_agent import AgentContext
    from src.core.orchestrator import Orchestrator, PipelineStep
    from src.agents.writer import WriterAgent
    from src.state.manager import StateManager

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    guidance = getattr(args, 'guidance', '') or ''
    word_count = getattr(args, 'words', 3000)

    log.info(f"📝 续写第 {args.chapter} 章: {args.name}")
    if guidance:
        log.info(f"   指导: {guidance}")

    # --model 覆盖
    model = getattr(args, 'model', None)
    if model:
        from src.utils.config import config as cfg
        cfg.set("model_name", model)
        log.info(f"   模型: {model}")

    context = AgentContext(
        project_dir=project_dir,
        user_guidance=guidance,
        extra={
            "chapter_number": args.chapter,
            "word_count": word_count,
        }
    )

    orchestrator = Orchestrator(project_dir)
    writer = WriterAgent()
    steps = [PipelineStep(agent=writer, required=True, resumable=False)]

    result = await orchestrator.run_sequential(steps, context)

    if result.success:
        final_extra = result.final_context.extra if result.final_context else {}
        chapter_text = final_extra.get("chapter_text", "")
        chapter_num = args.chapter

        state = StateManager(project_dir)
        saved = state.post_write(chapter_num, chapter_text)

        log.info(f"✅ 第 {chapter_num} 章完成!")
        log.info(f"   字数: {len(chapter_text)} 字")
        log.info(f"   保存: {saved['chapter_path']}")
    else:
        log.error(f"❌ 写稿失败: {result.error}")
        sys.exit(1)


async def cmd_style(args):
    """风格管理"""
    import os
    from src.core.base_agent import AgentContext
    from src.agents.style_analyzer import StyleAnalyzer

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    # 查看模式
    if args.show:
        style_path = os.path.join(project_dir, "style_guide.md")
        if os.path.exists(style_path):
            content = open(style_path, encoding="utf-8").read()
            log.info(f"📖 当前风格指南 ({len(content)} 字):\n")
            print(content)
        else:
            log.info("📖 暂无风格指南\n   使用 --file 或 --text 导入作家片段自动分析")
        return

    # 分析模式
    if args.file:
        if not os.path.exists(args.file):
            log.error(f"文件不存在: {args.file}")
            sys.exit(1)
        log.info(f"🎨 分析风格片段: {args.file}")
    elif args.text:
        log.info(f"🎨 分析风格文本 ({len(args.text)} 字)")
    else:
        log.error("需要 --file、--text 或 --show")
        sys.exit(1)

    context = AgentContext(
        project_dir=project_dir,
        user_guidance=args.text or "",
    )
    if args.file:
        context.extra = {"fragments_path": args.file}

    analyzer = StyleAnalyzer()
    result = await analyzer.safe_run(context)

    if result.success:
        length = result.context_updates.get("style_guide_length", 0)
        path = result.context_updates.get("style_guide_path", "")
        log.info(f"✅ 风格指南已生成 ({length} 字)")
        log.info(f"   保存: {path}")
        log.info(f"   写稿时将自动加载此风格")
    else:
        log.error(f"❌ 风格分析失败: {result.error}")
        sys.exit(1)


async def cmd_index(args):
    """构建向量索引"""
    import os
    from src.retrieval import VectorStore, index_project

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    log.info(f"🔍 构建向量索引: {args.name}")

    store = VectorStore(project_dir)

    if args.force:
        for col in store.list_collections():
            store.delete_collection(col)

    counts = index_project(project_dir, store)

    log.info(f"✅ 索引完成!")
    log.info(f"   foundations: {counts.get('foundations', 0)} 条")
    log.info(f"   chapters:    {counts.get('chapters', 0)} 条")
    log.info(f"   hooks:       {counts.get('hooks', 0)} 条")
    log.info(f"   写稿时将自动使用语义检索")


async def cmd_check(args):
    """后验校验"""
    import os
    from src.validation import CheckOrchestrator
    from src.retrieval import VectorStore

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    # 读取章节文本
    ext = getattr(args, 'ext', 'md')
    chapter_file = os.path.join(project_dir, "chapters", f"chapter_{args.chapter:04d}.{ext}")
    if not os.path.exists(chapter_file):
        chapter_file = os.path.join(project_dir, "chapters", f"chapter_{args.chapter:04d}.txt")
    if not os.path.exists(chapter_file):
        log.error(f"章节文件不存在: chapters/chapter_{args.chapter:04d}.md")
        sys.exit(1)

    chapter_text = open(chapter_file, encoding="utf-8").read()

    # 初始化 VectorStore（用于重复检测）
    store = None
    chroma_dir = os.path.join(project_dir, ".chroma")
    if os.path.exists(chroma_dir):
        try:
            store = VectorStore(project_dir)
        except Exception as e:
            log.warning(f"无法加载向量索引: {e}")
    else:
        log.info("   提示: 运行 'python main.py index --name \"{args.name}\"' 启用重复检测")

    checker = CheckOrchestrator(
        project_dir,
        skip_duplication=args.skip_dup,
        skip_ai_style=args.skip_ai,
        skip_consistency=args.skip_con,
    )

    report = checker.run(chapter_text, args.chapter, args.name, store)

    # Windows GBK 兼容：设置 UTF-8 输出
    import io
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    except Exception:
        pass

    print(report.format_cli())

    if report.has_errors():
        sys.exit(1)


async def cmd_status(args):
    """查看项目状态"""
    import os
    project_dir = get_project_dir(args.name)

    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    print(f"\n📖 {args.name}")
    print(f"   路径: {project_dir}")

    # 核心设定文件
    foundation_files = ["story_frame.md", "roles.md", "book_rules.md",
                        "volume_map.md", "style_guide.md", "Novel_setting.txt"]
    for fname in foundation_files:
        fpath = os.path.join(project_dir, fname)
        if os.path.exists(fpath):
            size = os.path.getsize(fpath)
            print(f"   📄 {fname}: {size} bytes")
        else:
            # 兼容旧文件位置
            for alt_dir in ["foundation", "story"]:
                alt_path = os.path.join(project_dir, alt_dir, fname)
                if os.path.exists(alt_path):
                    size = os.path.getsize(alt_path)
                    print(f"   📄 {alt_dir}/{fname}: {size} bytes")
                    break

    # 已写章节
    chapters_dir = os.path.join(project_dir, "chapters")
    if os.path.exists(chapters_dir):
        chapters = sorted([f for f in os.listdir(chapters_dir) if f.endswith((".md", ".txt"))])
        if chapters:
            print(f"\n   📝 已写章节: {len(chapters)} 章 ({chapters[0]} ~ {chapters[-1]})")
        else:
            print(f"\n   📝 已写章节: 0 章")
    else:
        print(f"\n   📝 已写章节: 0 章")

    # 状态文件
    state_dir = os.path.join(project_dir, "story", "state")
    if os.path.exists(state_dir):
        state_files = sorted(os.listdir(state_dir))
        if state_files:
            print(f"\n   📊 状态追踪 ({len(state_files)} 文件):")
            for sf in state_files:
                sp = os.path.join(state_dir, sf)
                print(f"      {sf}: {os.path.getsize(sp)} bytes")

    # 向量索引
    for idx_dir in [".chroma", "chroma_db"]:
        idx_path = os.path.join(project_dir, idx_dir)
        if os.path.exists(idx_path):
            print(f"\n   🔍 向量索引: {idx_dir}")


async def cmd_state(args):
    """查看角色状态"""
    import os
    from src.state.character_state import StateStore
    from src.state.tracker import StateTracker

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    store = StateStore(project_dir)
    chars = store.load()

    if not chars:
        log.info(f"📊 {args.name}: 暂无角色状态记录")
        log.info("   写完章节后会自动追踪角色状态")
        return

    tracker = StateTracker(project_dir)
    context = tracker.format_for_context(chars, max_chars=5000)
    print(context)


async def cmd_revise(args):
    """改写已有章节"""
    import os
    from src.core.base_agent import AgentContext
    from src.core.orchestrator import Orchestrator, PipelineStep
    from src.agents.revise import ReviseAgent

    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    guidance = getattr(args, 'guidance', '') or ''
    word_count = getattr(args, 'words', 3000)

    log.info(f"✏️ 改写第 {args.chapter} 章: {args.name}")
    if guidance:
        log.info(f"   指导: {guidance}")

    # --model 覆盖
    model = getattr(args, 'model', None)
    if model:
        from src.utils.config import config as cfg
        cfg.set("model_name", model)
        log.info(f"   模型: {model}")

    context = AgentContext(
        project_dir=project_dir,
        user_guidance=guidance,
        extra={
            "chapter_number": args.chapter,
            "word_count": word_count,
        },
    )

    orchestrator = Orchestrator(project_dir)
    reviser = ReviseAgent()
    steps = [PipelineStep(agent=reviser, required=True)]

    result = await orchestrator.run_sequential(steps, context)

    if result.success:
        updates = result.final_context.extra if result.final_context else {}
        log.info(f"✅ 第 {args.chapter} 章改写完成!")
        log.info(f"   字数: {updates.get('original_length', '?')} → {updates.get('revised_length', '?')}")
        log.info(f"   备份: {os.path.basename(updates.get('bak_path', ''))}")
    else:
        log.error(f"❌ 改写失败: {result.error}")
        sys.exit(1)


async def cmd_studio(args):
    """启动 Studio GUI"""
    import subprocess
    import os

    studio_path = os.path.join(os.path.dirname(__file__), "studio.py")
    log.info(f"🎨 启动 InkEdge Studio → http://localhost:8501")
    subprocess.run(["streamlit", "run", studio_path])


async def cmd_settle(args):
    """章节结算：Observer + 3 Settlers 全流程"""
    import os
    from src.settlement import SettlementOrchestrator
    from src.utils.llm_client import LLMClient
    from src.utils.file_io import read_file

    project_dir = f"projects/{args.name}"
    chapter_path = f"{project_dir}/chapters/chapter_{args.chapter:04d}.md"

    if not os.path.exists(chapter_path):
        print(f"❌ 第{args.chapter}章不存在: {chapter_path}")
        return

    chapter_text = read_file(chapter_path)
    llm = LLMClient()

    # 统计已有章数
    ch_dir = f"{project_dir}/chapters"
    chapter_count = len([f for f in os.listdir(ch_dir) if f.endswith('.md')]) if os.path.exists(ch_dir) else 0

    # 读取卷纲
    vol_path = f"{project_dir}/story/volumes.md"
    volume_outline = read_file(vol_path, default="") if os.path.exists(vol_path) else ""

    print(f"🔍 第{args.chapter}章结算中...")
    print(f"   1/4 Observer: 提取事实...")

    orch = SettlementOrchestrator(project_dir)
    report = await orch.settle(
        chapter_text, args.chapter, llm,
        chapter_count=chapter_count,
        volume_outline=volume_outline,
    )

    print(report.summary())
    print(f"\n📁 状态文件已更新: {project_dir}/story/state/")


async def cmd_radar(args):
    """市场雷达: scan / trends / cluster 分发"""
    from src.radar import RadarAgent
    from src.radar.sources import (
        FanqieRadarSource, QidianRadarSource, KnowledgeRadarSource,
    )
    from src.utils.llm_client import LLMClient

    src_map = {
        "fanqie": [FanqieRadarSource()],
        "qidian": [QidianRadarSource()],
        "all": [FanqieRadarSource(), QidianRadarSource()],
        "knowledge": [KnowledgeRadarSource()],
    }
    sources = src_map.get(args.source, [KnowledgeRadarSource()])
    llm = LLMClient()

    action = getattr(args, "radar_action", "scan")

    if action == "trends":
        await _cmd_radar_trends(args, sources, llm)
    elif action == "cluster":
        await _cmd_radar_cluster(args, llm)
    else:
        await _cmd_radar_scan(args, sources, llm)


async def _cmd_radar_scan(args, sources, llm):
    from src.radar import RadarAgent
    agent = RadarAgent(sources=sources)
    print(f"📡 市场雷达扫描: {args.genre or '全榜'} | 来源: {args.source}")
    report = await agent.scan(genre=args.genre, limit=args.limit, llm_client=llm)
    print(f"\n📊 趋势报告: {report.genre}")
    print(f"   数据量: {report.raw_entries_count} | 来源: {', '.join(report.sources)}")
    print(f"   {'─' * 40}")
    if report.summary:
        print(f"\n📝 趋势总结:\n   {report.summary}")
    if report.hot_tags:
        print(f"\n🏷️  热门标签: {', '.join(report.hot_tags)}")
    if report.trend_insights:
        print(f"\n🔍 趋势洞察:\n{report.trend_insights}")
    if report.writing_advice:
        print(f"\n💡 开书建议:\n{report.writing_advice}")


async def _cmd_radar_trends(args, sources, llm):
    from src.radar import RadarAgent
    agent = RadarAgent(sources=sources)
    print(f"📈 品类趋势识别: {args.source}")
    trends = await agent.identify_trends(limit=args.limit, llm_client=llm)
    print(f"\n{'=' * 50}")
    print(f"📊 {trends.get('summary', '')}")
    print(f"{'=' * 50}")
    for label, key in [("🚀 上升", "rising"), ("📉 下降", "declining"), ("➖ 稳定", "stable")]:
        items = trends.get(key, [])
        if items:
            print(f"\n{label}品类:")
            for item in items:
                c = item.get("category", "?")
                conf = item.get("confidence", 0)
                ev = item.get("evidence", "")
                print(f"   {c} (置信度: {conf:.0%})  {ev}")


async def _cmd_radar_cluster(args, llm):
    from src.radar import RadarAgent
    agent = RadarAgent()
    print(f"🔗 分类归并分析: {args.source}")
    cluster = await agent.cluster_genres(source=args.source, llm_client=llm)
    print(f"\n{'=' * 50}")
    print(f"📋 {args.source} 平台分类 → InkEdge 6 类归并方案")
    print(f"{'=' * 50}")
    if cluster.clusters:
        print(f"\n映射关系:")
        for c in cluster.clusters:
            src = c.get("platform_category", "?")
            dst = c.get("mapped_to", "?")
            conf = c.get("confidence", 0)
            print(f"   {src:　<6} → {dst:　<6}  (置信度: {conf:.0%})")
    if cluster.uncovered:
        print(f"\n⚠️  当前6类无法覆盖:")
        for u in cluster.uncovered:
            print(f"   - {u}")
    if cluster.suggested_new:
        print(f"\n💡 建议新建模块:")
        for s in cluster.suggested_new:
            print(f"   - {s}")


async def cmd_doctor(args):
    """环境诊断"""
    import json as _json
    from src.doctor import DoctorOrchestrator

    orch = DoctorOrchestrator(
        api_only=args.api_only,
        project=args.project,
    )
    report = await orch.run_async()

    if args.json:
        print(_json.dumps(report.to_json(), ensure_ascii=False, indent=2))
    else:
        print(report.format_cli())

    # --fix: 自动修复简单问题
    if args.fix:
        fixed = report.auto_fix()
        if fixed:
            print(f"  🔧 已自动修复 {fixed} 个问题")

    if report.has_errors():
        sys.exit(1)


async def cmd_analyze(args):
    """写作质量分析: density / foreshadow / conflict"""
    import os
    project_dir = get_project_dir(args.name)
    if not os.path.exists(project_dir):
        log.error(f"项目 '{args.name}' 不存在")
        sys.exit(1)

    mode = args.mode

    # 迁移先执行（避免分析时数据还是旧的）
    if args.migrate:
        from src.analysis import ForeshadowTracker
        ft = ForeshadowTracker(project_dir)
        count = ft.migrate_from_md()
        if count > 0:
            log.info(f"✅ 从 pending_hooks.md 迁移 {count} 条伏笔到 foreshadow.json")
        else:
            log.info("  无待迁移数据")

    if mode in ("density", "all"):
        from src.analysis import DensityAnalyzer
        da = DensityAnalyzer(project_dir)

        if args.fill:
            target = getattr(args, 'target', 'description') or 'description'
            log.info(f"💧 灌水模式: 提升 {target} 密度")
            report = da.analyze_fill(target_density=target)
        else:
            report = da.analyze()

        print(f"\n📊 {args.name} — 密度分析")
        print("-" * 55)
        if not report.stats:
            print("  无章节数据")
        else:
            hdr = f'{"章":>4} {"字数":>6} {"对话%":>6} {"动作%":>6} {"描写%":>6} {"内心%":>6}'
            print(hdr)
            print("-" * 55)
            for s in report.stats:
                print(f'{s.chapter:>4} {s.total_chars:>6} {s.dialogue_pct:>5.0f}% {s.action_pct:>5.0f}% {s.description_pct:>5.0f}% {s.inner_pct:>5.0f}%')

        if report.warnings:
            print(f"\n⚠️ 节奏警告:")
            for w in report.warnings:
                print(f"  {w}")
        if report.fill_suggestions:
            print(f"\n💧 灌水建议:")
            for f in report.fill_suggestions:
                print(f"  {f}")

    if mode in ("foreshadow", "all"):
        from src.analysis import ForeshadowTracker
        ft = ForeshadowTracker(project_dir)
        rpt = ft.report()
        print(f"\n🎯 {args.name} — 伏笔追踪")
        print(rpt.summary())

        if mode == "foreshadow" and args.list:
            for status, label in [("pending", "待回收"), ("reminded", "已提醒"), ("resolved", "已回收")]:
                items = getattr(rpt, status)
                if items:
                    print(f"\n  {label}:")
                    for h in items:
                        print(f"    {h.id}: {h.description[:60]}")

    if mode in ("conflict", "all"):
        from src.analysis import ConflictTracker
        ct = ConflictTracker(project_dir)
        report = ct.analyze()
        print(f"\n⚔️  {args.name} — 冲突追踪")
        print(report.summary())


def main():
    parser = argparse.ArgumentParser(
        description="InkEdge — Python 统一小说生成框架",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="可用命令")

    # templates — 列出模板
    subparsers.add_parser("templates", help="列出可用的写作方法论模板")

    # new — 创建新书
    p_new = subparsers.add_parser("new", help="创建新书（Architect 建书）")
    p_new.add_argument("--name", "-n", required=True, help="书名")
    p_new.add_argument("--topic", "-t", required=True, help="故事主题")
    p_new.add_argument("--genre", "-g", default="奇幻", help="类型")
    p_new.add_argument("--chapters", "-c", type=int, default=60, help="目标章数")
    p_new.add_argument("--words", "-w", type=int, default=3000, help="每章字数")
    p_new.add_argument("--template", default="unified", help="写作方法论模板（默认: unified）")
    p_new.add_argument("--from-dir", "-d", help="从已有材料目录加载（读取 .md/.txt，忠实转写为 foundation）")
    p_new.add_argument("--wizard", action="store_true", help="交互式逐步建书：每步生成后暂停，供作者审核修改")
    p_new.add_argument("--model", "-m", help="指定模型（如 deepseek-v4-pro）")

    # write — 写稿
    p_write = subparsers.add_parser("write", help="续写章节")
    p_write.add_argument("--name", "-n", required=True, help="书名")
    p_write.add_argument("--chapter", "-c", type=int, required=True, help="章号")
    p_write.add_argument("--guidance", "-g", help="本章写作指导")
    p_write.add_argument("--words", "-w", type=int, default=3000, help="目标字数")
    p_write.add_argument("--model", "-m", help="指定模型（如 deepseek-v4-pro）")

    # revise — 改写章节
    p_revise = subparsers.add_parser("revise", help="改写已有章节")
    p_revise.add_argument("--name", "-n", required=True, help="书名")
    p_revise.add_argument("--chapter", "-c", type=int, required=True, help="章号")
    p_revise.add_argument("--guidance", "-g", help="修改指导（如：加强战斗描写、增加对话密度）")
    p_revise.add_argument("--words", "-w", type=int, default=3000, help="目标字数")
    p_revise.add_argument("--model", "-m", help="指定模型（如 deepseek-v4-pro）")

    # style — 风格分析
    p_style = subparsers.add_parser("style", help="风格管理")
    p_style.add_argument("--name", "-n", required=True, help="书名")
    p_style.add_argument("--file", "-f", help="作家片段文件（分析并生成 style_guide.md）")
    p_style.add_argument("--text", "-t", help="直接输入风格片段文本")
    p_style.add_argument("--show", "-s", action="store_true", help="查看当前风格指南")

    # index — 向量索引
    p_index = subparsers.add_parser("index", help="构建向量索引（语义检索）")
    p_index.add_argument("--name", "-n", required=True, help="书名")
    p_index.add_argument("--force", "-f", action="store_true", help="强制重建索引")

    # check — 后验校验
    p_check = subparsers.add_parser("check", help="后验校验（重复检测 + AI痕迹评估 + 一致性校验）")
    p_check.add_argument("--name", "-n", required=True, help="书名")
    p_check.add_argument("--chapter", "-c", type=int, required=True, help="章号")
    p_check.add_argument("--skip-dup", action="store_true", help="跳过重复检测")
    p_check.add_argument("--skip-ai", action="store_true", help="跳过 AI 痕迹评估")
    p_check.add_argument("--skip-con", action="store_true", help="跳过一致性校验")

    # state — 角色状态
    p_state = subparsers.add_parser("state", help="查看角色状态追踪")
    p_state.add_argument("--name", "-n", required=True, help="书名")

    # settle — 章节结算
    p_settle = subparsers.add_parser("settle", help="章节结算（Observer + 3 Settlers 全流程）")
    p_settle.add_argument("--name", "-n", required=True, help="书名")
    p_settle.add_argument("--chapter", "-c", type=int, required=True, help="章号")

    # status — 项目状态
    p_status = subparsers.add_parser("status", help="查看项目状态")
    p_status.add_argument("--name", "-n", required=True, help="书名")

    # radar — 市场雷达
    p_radar = subparsers.add_parser("radar", help="市场雷达（扫描排行榜分析趋势）")
    p_radar_sub = p_radar.add_subparsers(dest="radar_action")
    p_radar_scan = p_radar_sub.add_parser("scan", help="扫描排行榜 + 趋势分析")
    p_radar_scan.add_argument("--genre", "-g", default="", help="类型过滤（空=全榜）")
    p_radar_scan.add_argument("--source", "-s", default="knowledge", help="数据源: fanqie/qidian/all/knowledge")
    p_radar_scan.add_argument("--limit", "-l", type=int, default=30, help="返回条数")
    p_radar_trends = p_radar_sub.add_parser("trends", help="识别上升/下降品类")
    p_radar_trends.add_argument("--source", "-s", default="knowledge", help="数据源")
    p_radar_trends.add_argument("--limit", "-l", type=int, default=50)
    p_radar_cluster = p_radar_sub.add_parser("cluster", help="分析平台分类→创作品类归并")
    p_radar_cluster.add_argument("--source", "-s", default="all", help="平台: fanqie/qidian/all")

    # doctor — 环境诊断
    p_doctor = subparsers.add_parser("doctor", help="环境诊断（Python/依赖/配置/API/项目）")
    p_doctor.add_argument("--api-only", action="store_true", help="仅检查 API 连通性")
    p_doctor.add_argument("--project", help="检查特定项目")
    p_doctor.add_argument("--json", action="store_true", help="JSON 输出（供脚本调用）")
    p_doctor.add_argument("--fix", action="store_true", help="自动修复简单问题")

    # analyze — 写作质量分析
    p_analyze = subparsers.add_parser("analyze", help="写作质量分析（密度/伏笔/冲突）")
    p_analyze.add_argument("--name", "-n", required=True, help="书名")
    p_analyze.add_argument("--mode", "-m", default="all",
                           choices=["density", "foreshadow", "conflict", "all"],
                           help="分析模式 (默认: all)")
    p_analyze.add_argument("--fill", action="store_true",
                           help="灌水模式: 找出密度偏低的章节, 给扩展建议")
    p_analyze.add_argument("--target", choices=["dialogue", "action", "description", "inner"],
                           default="description", help="灌水目标类型")
    p_analyze.add_argument("--list", action="store_true",
                           help="列出所有伏笔详情")
    p_analyze.add_argument("--migrate", action="store_true",
                           help="从 pending_hooks.md 迁移伏笔到结构化格式")

    # studio — GUI
    subparsers.add_parser("studio", help="启动 Studio GUI")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    # 路由到对应命令
    commands = {
        "new": cmd_new,
        "templates": cmd_templates,
        "write": cmd_write,
        "revise": cmd_revise,
        "style": cmd_style,
        "index": cmd_index,
        "check": cmd_check,
        "state": cmd_state,
        "settle": cmd_settle,
        "radar": cmd_radar,
        "status": cmd_status,
        "studio": cmd_studio,
        "doctor": cmd_doctor,
        "analyze": cmd_analyze,
    }

    cmd_func = commands.get(args.command)
    if cmd_func:
        asyncio.run(cmd_func(args))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
