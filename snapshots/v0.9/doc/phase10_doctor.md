# Phase 10 — 环境诊断（Environment Doctor）

> 版本：0.1（设计稿）
> 日期：2026-05-24
> 状态：设计阶段
> 来源：inkOS 同名功能

---

## 一、问题定义

### 1.1 当前痛点

InkEdge 目前没有自检能力。出了问题用户只能看到一堆 Python traceback，无法快速定位是：
- Python 版本太旧？
- 缺少某个 pip 包？
- API Key 填错了？
- DeepSeek 服务不通？
- ChromaDB 文件损坏？
- 嵌入模型没下载？

### 1.2 Doctor 做什么

一条命令跑完所有检查，输出清晰的 pass/fail 列表，每个失败项都有**人类可读的修复建议**。

---

## 二、检查维度

### 2.1 检查清单

```
┌─ 环境层 ───────────────────────────────┐
│ Python 版本          ≥ 3.10             │
│ pip 核心包           aiohttp/chromadb   │
│   sentence-transformers 模型已缓存      │
│   ChromaDB 可读写                      │
│ 操作系统             已知兼容             │
└────────────────────────────────────────┘
┌─ 配置层 ───────────────────────────────┐
│ config.yaml          存在 + 格式正确      │
│ base_url             可解析             │
│ model_name           非空               │
│ API Key              (可选) 格式正确      │
└────────────────────────────────────────┘
┌─ 连接层 ───────────────────────────────┐
│ API 连通性           发测试请求 → "OK"  │
│   模型可用性         指定模型存在        │
│   响应延迟           < 5s               │
│   回退模型           (可选) 可用         │
└────────────────────────────────────────┘
┌─ 项目层 ───────────────────────────────┐
│ projects/             存在               │
│ 项目数                N 个               │
│ 项目完整性            必要文件齐全        │
│ ChromaDB 索引状态     有/无/损坏         │
└────────────────────────────────────────┘
```

### 2.2 检查严重性

| 级别 | 含义 | 处理 |
|------|------|------|
| `error` | 核心功能完全不可用 | 必须先修 |
| `warning` | 部分功能受限 | 建议修 |
| `info` | 纯粹信息 | 无需处理 |

---

## 三、各检查项详细设计

### 3.1 Python 版本

```python
import sys
version = sys.version_info
ok = version >= (3, 10)
detail = f"Python {version.major}.{version.minor}.{version.micro}"
hint = "需要 Python 3.10+，请升级" if not ok else ""
```

### 3.2 核心依赖

```python
REQUIRED_PACKAGES = [
    ("aiohttp", "异步 HTTP 客户端（LLM 调用）"),
    ("chromadb", "向量数据库（语义检索）"),
    ("sentence_transformers", "本地嵌入模型"),
    ("yaml", "配置文件解析"),
]

for pkg, desc in REQUIRED_PACKAGES:
    try:
        __import__(pkg)
        checks.append(("ok", f"{pkg} ({desc})", f"v{version}"))
    except ImportError:
        checks.append(("error", f"{pkg} 未安装 ({desc})", 
                       f"pip install {pkg}"))
```

### 3.3 嵌入模型缓存

```python
# 检查 sentence-transformers 模型是否已下载到本地缓存
cache_paths = [
    Path.home() / ".cache/huggingface/hub/models--sentence-transformers--paraphrase-multilingual-MiniLM-L12-v2",
    Path.home() / ".cache/chroma/onnx_models/all-MiniLM-L6-v2",
]

for path in cache_paths:
    if path.exists():
        model_file = next(path.rglob("*.safetensors"), None)
        if model_file:
            checks.append(("ok", f"嵌入模型已缓存", f"{model_file.stat().st_size/1e6:.0f}MB"))
        else:
            checks.append(("warning", "嵌入模型目录存在但缺少模型文件", "删除缓存后重试"))
    else:
        checks.append(("warning", "嵌入模型未缓存", "首次使用时将自动下载（需联网）"))
```

### 3.4 ChromaDB 读写测试

```python
import tempfile, os, shutil
tmp = tempfile.mkdtemp()
try:
    import chromadb
    client = chromadb.PersistentClient(path=tmp)
    col = client.create_collection("_doctor_test")
    col.add(documents=["test"], ids=["1"])
    result = col.get("1")
    ok = result["documents"][0] == "test"
finally:
    shutil.rmtree(tmp, ignore_errors=True)
```

### 3.5 config.yaml 检查

```python
import yaml
config_path = Path("config.yaml")

if not config_path.exists():
    checks.append(("error", "config.yaml 不存在", "从模板复制或运行 python main.py"))
else:
    with open(config_path) as f:
        config = yaml.safe_load(f)
    
    # 必须字段
    for key in ["base_url", "model_name"]:
        if not config.get(key):
            checks.append(("error", f"config.yaml 缺少 {key}", f"在 config.yaml 中设置 {key}"))
    
    # API Key 格式检查（不验证有效性）
    api_key = config.get("api_key", "")
    if not api_key:
        checks.append(("warning", "API Key 未设置", "在 config.yaml 或环境变量中设置"))
    elif len(api_key) < 10:
        checks.append(("error", "API Key 格式异常（太短）", "检查 API Key 是否正确"))
```

### 3.6 API 连通性测试

```python
from src.utils.llm_client import LLMClient

client = LLMClient()
try:
    response = await client.chat(
        prompt="回复 OK（只回复这两个字母，不要其他内容）",
        max_tokens=5,
    )
    ok = "OK" in response.content.upper()
    latency = ...  # 记录响应延迟
    
    if ok:
        checks.append(("ok", f"LLM API 连通", 
                       f"模型 {response.model} · {response.usage.total_tokens} tokens · {latency:.1f}s"))
    else:
        checks.append(("warning", "LLM 响应异常", f"返回: {response.content[:100]}"))
except Exception as e:
    error_msg = str(e)
    hint = ""
    if "401" in error_msg or "unauthorized" in error_msg:
        hint = "API Key 无效，检查 config.yaml 中的 api_key"
    elif "403" in error_msg or "forbidden" in error_msg:
        hint = "API Key 无权限访问该模型，检查模型名和账户状态"
    elif "429" in error_msg:
        hint = "API 速率限制或配额耗尽，稍后重试"
    elif "Connection" in error_msg or "ECONNREFUSED" in error_msg:
        hint = "无法连接 base_url，检查网络和地址"
    elif "timeout" in error_msg.lower():
        hint = "连接超时，base_url 可能不正确或服务端无响应"
    
    checks.append(("error", "LLM API 不可用", error_msg[:100]))
    if hint:
        checks.append(("info", "  💡 提示", hint))
```

### 3.7 项目完整性检查

```python
projects_dir = Path("projects")
if projects_dir.exists():
    for proj in projects_dir.iterdir():
        if proj.is_dir():
            required_files = ["story_frame.md", "roles.md", "book_rules.md"]
            missing = [f for f in required_files if not (proj / f).exists()]
            
            if missing:
                checks.append(("warning", f"项目 {proj.name} 缺少文件", 
                               f"缺失: {', '.join(missing)}"))
            
            # ChromaDB 索引状态
            chroma_dir = proj / ".chroma"
            if chroma_dir.exists():
                # 统计 collection 和文档数
                ...
```

### 3.8 ChromaDB 索引健康检查

```python
from src.retrieval import VectorStore

store = VectorStore(str(proj))
collections = store.list_collections()
for col_name in collections:
    count = store.count(col_name)
    checks.append(("info", f"索引 {proj.name}/{col_name}", f"{count} 条"))
```

---

## 四、CLI 设计

```bash
# 运行全部检查
python main.py doctor

# 只检查 API 连通性
python main.py doctor --api-only

# 检查特定项目
python main.py doctor --project "无名密探"

# JSON 输出（供脚本调用）
python main.py doctor --json

# 自动修复简单问题
python main.py doctor --fix
```

### 输出示例

```
🩺 InkEdge Doctor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  环境层
  ✅ Python 3.11.0
  ✅ aiohttp v3.9.0
  ✅ chromadb v0.5.0
  ✅ 嵌入模型已缓存 (470MB)
  ✅ ChromaDB 可读写

  配置层
  ✅ config.yaml 存在
  ✅ base_url: https://api.deepseek.com/v1
  ✅ model_name: deepseek-v4-flash
  ⚠️ api_key 未设置（将在首次 LLM 调用时报错）

  连接层
  ✅ LLM API 连通 (模型 deepseek-v4-flash · 127 tokens · 1.2s)

  项目层
  ✅ projects/ 存在
  📖 无名密探 (悬疑奇幻)
     ✅ 核心文件齐全
     📊 索引: foundations(6) chapters(8) hooks(5)
  📖 蒸汽宋歌 (历史科幻)
     ⚠️ 缺少 story_frame.md → 运行 python main.py new

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  2 个警告 ⚠️
  0 个错误 ✅
```

---

## 五、文件结构

```
src/doctor/
├── __init__.py
├── checker.py              # DoctorOrchestrator — 所有检查项的调度
├── checks_env.py           # 环境层检查（Python / 依赖 / 模型缓存 / ChromaDB）
├── checks_config.py        # 配置层检查（config.yaml / base_url / model）
├── checks_api.py           # 连接层检查（API 连通 / 模型可用 / 回退模型）
├── checks_project.py       # 项目层检查（文件完整性 / 索引状态）
└── report.py               # DoctorReport 数据类 + 格式化输出
```

---

## 六、与配置系统的关系

Doctor 是只读工具——只检查、不修改。`--fix` 模式也只修简单问题：
- 创建缺失的目录
- 生成模板 config.yaml
- 清理损坏的 ChromaDB 文件

不自动修改 API Key 或删除项目文件。

---

## 七、未来改进方向

### 7.1 启动时自动运行（v1.1）

```python
# main.py 启动时
if not os.environ.get("NOVELFORGE_SKIP_DOCTOR"):
    quick_checks = run_quick_check()  # 只做 Python 版本 + config 存在
    if quick_checks.has_errors:
        print("⚠️ 检测到环境问题，运行 python main.py doctor 查看详情")
```

### 7.2 定时健康检查（v1.2）

用 cron job 每天跑一次 doctor，结果写入 `doctor.log`。

### 7.3 性能基准（v2.0）

不只是 pass/fail，还记录性能基线：
- LLM 响应速度
- 嵌入编码速度
- ChromaDB 查询延迟
- 用于后续性能回归检测

### 7.4 GUI 集成（v2.1）

在 Streamlit 中展示可视化的 Doctor 面板：
- 绿色/黄色/红色状态指示灯
- 一键修复按钮
- 历史检查记录

---

## 八、决策记录

- **2026-05-24**：从 inkOS doctor 移植设计。核心差异：inkOS 检查 Node.js/SQLite 版本，InkEdge 检查 Python/pip 依赖/嵌入模型缓存。
- Doctor 是只读工具，`--fix` 仅修简单问题（创建目录/模板文件）。
- API 连通性测试发送最小化请求（"回复 OK"），不计入用户 Token 统计，但能完整验证端到端可用性。
