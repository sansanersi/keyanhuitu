# 科研配图AI系统 — 完整复现清单

> 本文档提供了从零开始搭建科研配图AI系统的每一步详细说明。
> 适用环境: Windows + Anaconda Python 3.11 + Ollama

---

## 1. 环境准备

### 1.1 Python 环境

```powershell
# 检查 Python
python --version                    # 需要 >= 3.8
pip --version

# 安装依赖（基础包已预装）
pip install numpy scipy              # 向量计算
pip install flask                    # Web 管理界面
pip install requests                 # HTTP 请求
pip install pdfplumber               # PDF 文档提取（可选）
pip install python-docx              # Word 文档提取（可选）
```

### 1.2 Ollama 安装

```powershell
# 1. 从 https://ollama.com 下载安装包
# 2. 启动 Ollama 服务
$env:OLLAMA_HOST = "127.0.0.1:11434"
ollama serve

# 3. 拉取模型（需要网络，用于中文科研文本分析）
ollama pull qwen3.5:4b               # 推荐，均衡模型 (~3GB)
# ollama pull qwen3.5:0.8b           # 轻量级 (~1GB)
# ollama pull gemma3:4b             # 英文优先 (~3GB)

# 4. 验证
ollama list
```

> **无网络环境**: 从 HuggingFace 下载 GGUF 文件后，创建 Modelfile:
> ```
> FROM ./qwen3.5-4b-instruct-q4_K_M.gguf
> ```
> 再 `ollama create qwen3.5:4b -f Modelfile`

---

## 2. 项目结构

将以下完整目录复制到目标机器:

```
sci_knowledge_base/         ← 独立知识库包（可 pip install）
sci-illust-system/          ← 主系统
├── knowledge_base/         ← 知识库引擎 (RAG + 向量检索)
├── drawing/                ← 绘图引擎 (SVG + 布局 + 风格)
├── orchestrator/           ← LLM 编排管道
├── evaluation/             ← 质量评估系统
├── ollama_integration/     ← Ollama 本地模型集成
├── web_app/                ← Flask 管理界面 ← 核心
├── data/                   ← 数据文件
├── examples/               ← 使用示例
└── tests/                  ← 测试脚本
```

---

## 3. 启动系统

### 3.1 一键启动管理界面

```powershell
cd C:\Users\qinsh\Desktop\new_word
$env:PYTHONPATH = "C:\Users\qinsh\Desktop\new_word"
python sci-illust-system\web_app\app.py
```

打开浏览器访问 http://127.0.0.1:5000

### 3.2 确保 Ollama 服务在运行

```powershell
# 检查 Ollama 是否运行
$env:OLLAMA_HOST = "127.0.0.1:11434"
ollama list

# 如果没运行:
ollama serve
```

### 3.3 分步测试各模块

```powershell
# 1. 测试知识库
python -c "from sci_knowledge_base import KnowledgeBase; kb=KnowledgeBase(); print(kb)"
python -m sci_knowledge_base.cli stats

# 2. 测试绘图引擎
cd sci-illust-system
python -c "
from drawing.element_gen import SVGElementGenerator
g = SVGElementGenerator()
print(g.generate('线粒体', 'bean', ['#E74C3C','#C0392B'], {'width':80,'height':60})[:80])
"

# 3. 测试 Ollama 集成
cd sci-illust-system
python -c "
from ollama_integration.ollama_client import OllamaClient
c = OllamaClient()
print('Ollama:', c.is_available)
print('Models:', c.list_models())
"

# 4. 端到端流水线
python -c "
from orchestrator.pipeline import SciIllustPipeline
p = SciIllustPipeline()
p.process_and_save('EGF配体结合EGFR受体，激活RAS激酶', 'test.svg')
print('SVG 已生成')
"
```

---

## 4. 功能清单

### ✅ 已实现功能

| 功能 | 模块 | 使用方式 |
|------|------|----------|
| 领域知识库 (53术语, 4学科) | `sci_knowledge_base` | `kb.query("细胞膜")` |
| RAG 向量检索 | `kb_core.py` | 自然语言搜索 |
| SVG 元素生成 (50种形状) | `element_gen.py` | 自动配图 |
| 四种布局算法 | `layout_engine.py` | 力导向/层级/网格/径向 |
| 五套预置风格 | `style_engine.py` | Nature/Cell/科学/极简/色盲友好 |
| 需求文本分析 | `text_analyzer.py` | 自动识别学科和图类型 |
| 元素关系提取 | `text_analyzer.py` | 从文本提取激活/抑制/结合关系 |
| 三维质量评估 | `evaluator.py` | 完整性40%+布局35%+可编辑25% |
| Ollama 本地 LLM 集成 | `ollama_integration/` | 支持 qwen/llama/gemma |
| Web 管理界面 | `web_app/` | Flask + 单页应用 |
| 文档上传自动向量化 | `web_app/` | 自动提取术语入知识库 |
| SQLite 数据库 CRUD | `web_app/database.py` | 手动编辑知识条目 |
| Dify API 桥接 | `web_app/dify_bridge.py` | 将 Dify 作为 LLM 后端 |

---

## 5. 使用方式

### 5.1 Web 管理界面（推荐）

```powershell
cd C:\Users\qinsh\Desktop\new_word
$env:PYTHONPATH = "C:\Users\qinsh\Desktop\new_word"
python sci-illust-system\web_app\app.py
```

浏览器打开 http://127.0.0.1:5000

左侧导航:
- 📊 仪表盘 — 系统概览
- 📚 知识条目 — 增删改查知识库
- 📄 文档管理 — 上传文档自动向量化
- 🔍 知识检索 — RAG 搜索 + LLM 分析
- 🎨 元素库 — 浏览可绘制元素
- 🔗 Dify 集成 — 配置 Dify API
- ⚙️ 设置 — Ollama 状态等

### 5.2 Python API

```python
from sci_knowledge_base import KnowledgeBase
from orchestrator.pipeline import SciIllustPipeline
from ollama_integration.ollama_client import OllamaClient

# 知识库搜索
kb = KnowledgeBase()
results = kb.query("细胞膜受体信号")

# 端到端绘图
pipeline = SciIllustPipeline()
pipeline.process_and_save("纳米颗粒靶向癌细胞", "output.svg")

# Ollama LLM
client = OllamaClient()
resp = client.chat([{"role":"user","content":"分析这段需求..."}])
```

### 5.3 命令行

```powershell
# 知识库查询
python -m sci_knowledge_base.cli query "DNA 转录"
python -m sci_knowledge_base.cli info 线粒体
python -m sci_knowledge_base.cli domain biology

# 运行演示
python sci-illust-system/examples/demo_usage.py
```

---

## 6. 数据管理

### 知识条目管理

Web 界面中:

- **新增**: 点击 "+ 新增条目" 按钮，填写名称、学科、形状等
- **编辑**: 点击条目后的 "编辑" 按钮
- **删除**: 点击 "删除" 按钮
- **搜索**: 在搜索框输入关键词过滤
- **学科筛选**: 下拉选择按学科查看

### 文档自动向量化

1. 进入 "文档管理" 页面
2. 选择文件（支持 .txt, .md, .pdf, .docx, .csv）
3. 点击 "上传并向量化"
4. 系统自动提取中文术语并写入知识库
5. 可在 "知识条目" 中查看和编辑自动生成的条目

### 数据库文件

```
sci-illust-system/web_app/data/knowledge.db  ← SQLite 数据库
sci-illust-system/web_app/data/uploads/      ← 上传文档存储
```

---

## 7. Dify 集成

### 7.1 配置 Dify

1. 打开 Web 界面 → Dify 集成
2. 填写 Dify API 地址（如 `http://localhost:8080/api`）
3. 填写 API Key
4. 点击 "测试连接"

### 7.2 将知识库作为 Dify 工具

在 Dify 中创建自定义工具，填入以下配置:

```json
{
  "name": "sci_illust_knowledge",
  "openapi": {
    "info": {"title": "科研配图知识库", "version": "1.0.0"},
    "paths": {
      "/api/search": {
        "get": {
          "summary": "检索科研配图知识库",
          "parameters": [
            {"name": "q", "in": "query", "required": true, "schema": {"type": "string"}}
          ],
          "responses": {"200": {"description": "匹配的术语列表"}}
        }
      }
    }
  }
}
```

---

## 8. 模型选择建议

| 模型 | 大小 | 速度 | 适用场景 |
|------|------|------|----------|
| qwen3.5:0.8b | ~1GB | ~3秒 | 快速测试、简单元素列表 |
| qwen3.5:4b | ~3GB | ~24秒 | 日常科研需求分析 **推荐** |
| qwen3.5:9b | ~6GB | ~60秒 | 复杂机制图、长文本分析 |
| gemma3:4b | ~3GB | ~37秒(首次) | 英文科研文本 |

---

## 9. 常见问题

### Q: Ollama 启动报 "Access is denied"

```powershell
# 清理旧日志文件
taskkill /F /IM ollama.exe
Remove-Item "$env:LOCALAPPDATA\Ollama\*.log" -Force
ollama serve
```

### Q: 模型响应为空

qwen3.5 是 reasoning 模型，响应在 `thinking` 字段。系统已自动处理此兼容性。

### Q: 如何添加更多知识条目

- Web 界面: 📚 知识条目 → + 新增条目
- 上传文档: 📄 文档管理 → 上传并向量化
- 直接编辑 JSON: `sci_knowledge_base/data/domain_vocab.json`

### Q: 如何修改配色/风格

编辑 `sci_knowledge_base/data/color_schemes/default_scheme.json`

---

## 10. 文件索引

| 文件 | 用途 |
|------|------|
| `sci_knowledge_base/kb_core.py` | 知识库引擎核心 |
| `sci_knowledge_base/element_library.py` | 元素模板管理 |
| `sci_knowledge_base/cli.py` | 命令行工具 |
| `sci-illust-system/drawing/element_gen.py` | 50种SVG图元生成 |
| `sci-illust-system/drawing/layout_engine.py` | 四种布局算法 |
| `sci-illust-system/drawing/renderer.py` | SVG渲染器 |
| `sci-illust-system/drawing/style_engine.py` | 风格管理 |
| `sci-illust-system/orchestrator/pipeline.py` | 主工作流管道 |
| `sci-illust-system/orchestrator/text_analyzer.py` | 需求分析器 |
| `sci-illust-system/evaluation/evaluator.py` | 三维评估系统 |
| `sci-illust-system/ollama_integration/ollama_client.py` | Ollama API客户端 |
| `sci-illust-system/ollama_integration/pipeline_bridge.py` | LLM+知识库桥接 |
| `sci-illust-system/ollama_integration/server_manager.py` | Ollama服务管理 |
| `sci-illust-system/web_app/app.py` | Flask 管理后端 |
| `sci-illust-system/web_app/database.py` | SQLite 数据库 |
| `sci-illust-system/web_app/dify_bridge.py` | Dify API桥接 |
| `sci-illust-system/web_app/document_processor.py` | 文档向量化 |
| `sci-illust-system/web_app/templates/index.html` | 前端管理界面 |

---

> **版本**: v1.0 | **更新日期**: 2026-07-21 | **Python**: 3.11+ | **Ollama**: 0.32.1
