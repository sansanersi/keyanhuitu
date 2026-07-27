# 科研配图AI系统 (Sci-Illust AI System)

## 概述

基于 **知识库 + 绘图引擎 + LLM编排 + 评估系统 + 本地模型** 五层架构的科研配图自动化生产系统。

## 系统架构

```
用户输入 (文本需求)
    │
┌───▼────────────────────────────────────────────────┐
│  ① 知识库 (Knowledge Base + RAG)                   │
│  53个专业术语, 4学科, 向量检索                     │
└──────────────────┬─────────────────────────────────┘
                   │
┌───▼────────────────────────────────────────────────┐
│  ② 绘图引擎 (Drawing Engine)                       │
│  50种SVG图元, 4种布局算法, 5种风格                 │
└──────────────────┬─────────────────────────────────┘
                   │
┌───▼────────────────────────────────────────────────┐
│  ③ LLM编排层 (Ollama 本地 / 模拟)                  │
│  ├─ Ollama 本地模型 (qwen2.5/llama3)              │
│  └─ 模拟分析器 (KB回退)                            │
└──────────────────┬─────────────────────────────────┘
                   │
┌───▼────────────────────────────────────────────────┐
│  ④ 评估系统 (Evaluation)                           │
│  完整性40% + 布局35% + 可编辑性25%                 │
└──────────────────┬─────────────────────────────────┘
                   │
                   ▼
           可编辑SVG科研配图
```

## Ollama 本地模型部署

### 前提条件

Ollama v0.32.1 已安装在系统上: `C:\Users\qinsh\AppData\Local\Programs\Ollama\ollama.exe`

### 启动服务器

```powershell
# 启动服务器
ollama serve

# 或通过Python
python examples/setup_ollama.py
```

### 拉取模型 (需要网络)

```powershell
ollama pull qwen2.5:3b      # 中文科研文本 (~2GB)
ollama pull nomic-embed-text # RAG嵌入 (~0.3GB)
```

### 离线部署 (无网络)

1. 从 HuggingFace 下载 GGUF 文件
2. 创建 Modelfile: `FROM ./model.gguf`
3. 导入: `ollama create qwen2.5:3b -f Modelfile`

### 集成模块

```python
from ollama_integration.pipeline_bridge import OllamaPipelineBridge

bridge = OllamaPipelineBridge()
bridge.ensure_server()           # 启动Ollama服务器
result = bridge.analyze_requirement("细胞信号通路", kb)
```

## 使用

```python
from orchestrator.pipeline import SciIllustPipeline
pipeline = SciIllustPipeline()
result = pipeline.process("EGF配体结合EGFR受体，激活RAS激酶...", auto_render=True)
pipeline.process_and_save("需求文本", "output.svg")
```

## 项目结构

```
sci-illust-system/
├── knowledge_base/      知识库 + RAG引擎
├── drawing/             绘图引擎 (SVG + 布局 + 风格)
├── orchestrator/        LLM编排层 (模拟/本地)
├── evaluation/          质量评估系统
├── ollama_integration/  Ollama 本地模型部署
│   ├── ollama_client.py     API客户端
│   ├── server_manager.py    服务器生命周期管理
│   ├── pipeline_bridge.py   集成桥 (LLM + RAG)
│   └── __init__.py
├── data/                数据文件 (词汇库, 配色)
├── examples/            示例脚本
├── tests/               测试
├── README.md
└── requirements.txt
```

## 评估维度

| 维度 | 权重 | 说明 |
|------|:----:|------|
| 元素完整性 | 40% | 需求元素覆盖率 |
| 布局合理性 | 35% | 重叠/对齐/间距 |
| 可编辑性 | 25% | SVG标注/分组/颜色 |
