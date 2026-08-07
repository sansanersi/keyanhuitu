# 科研绘图系统架构拆分设计

## 1. 目标

当前系统正在从“科研绘图工作台”升级为“科研绘图平台”。平台不应把文本管理、图片资产管理、模型编排和生成图全部塞进一个页面或一个业务模块，而应拆成清晰的数据资产层和最终应用层。

本设计的目标是先明确架构边界，再讨论代码迁移。

核心原则：

- 文本库负责知识。
- 图片库负责素材。
- 应用平台负责生成。
- 一个 MySQL 实例承载三个逻辑库：`text_db`、`image_db`、`app_db`。
- 第一阶段优先做逻辑拆分，不急于拆成多个独立部署服务。

## 2. 总体架构

```text
科研绘图平台
├─ 文本库系统
├─ 图片库系统
├─ 科研绘图应用平台
└─ 数据与索引底座
```

数据流：

```text
客户需求
  ↓
科研绘图应用平台
  ↓
读取 text_db / RAG / GraphRAG
  ↓
读取 image_db / 本地图片文件 / 图数据库
  ↓
LLM 生成 AI 绘图流程
  ↓
元素匹配与构图
  ↓
生成图
  ↓
保存项目结果到 app_db
```

## 3. 数据库拆分

采用一个 MySQL 实例，三个逻辑库。

```text
MySQL 实例
├─ text_db
├─ image_db
└─ app_db
```

这样做的原因：

- 检索效果不取决于几个 MySQL 实例，而取决于数据质量、索引、Embedding、标签和召回策略。
- 一个 MySQL 实例更容易开发、备份、迁移和排查。
- 三个逻辑库可以先保证边界清晰，后期如果数据量或权限要求变大，再拆成独立实例。
- 应用平台可以直接跨逻辑库读取，不需要一开始引入复杂的微服务通信。

## 4. 文本库系统

文本库系统是科研绘图平台的知识资产系统。

职责：

- 管理论文、图注、术语、客户需求、实验描述、绘图说明。
- 做文本清洗、分段、结构化。
- 维护术语、别名、学科、标签。
- 生成 RAG 检索索引。
- 生成 GraphRAG 实体与关系。
- 向应用平台提供可检索的知识上下文。

建议逻辑表：

```text
text_db.documents
text_db.document_chunks
text_db.terms
text_db.term_aliases
text_db.figure_captions
text_db.customer_requirements
text_db.text_embeddings
text_db.graphrag_entities
text_db.graphrag_relations
text_db.import_jobs
```

文本库不负责：

- 不负责生成最终科研配图。
- 不负责管理图片文件。
- 不负责项目版本和导出记录。

## 5. 图片库系统

图片库系统是科研绘图平台的视觉资产系统。

职责：

- 管理原始图片、线稿图、SVG 图元、Bioicons、历史生成图、客户参考图。
- 维护图片路径、来源、标签、学科、用途。
- 维护图片中的元素标注。
- 建立图片、元素、学科、画法之间的关系网络。
- 支持相似图片检索和可复用图元推荐。
- 向应用平台提供可绘制素材和参考图。

存储方式：

```text
本地文件系统
└─ image_assets/

MySQL
└─ image_db

图数据库
└─ image_element_graph
```

建议逻辑表：

```text
image_db.images
image_db.image_files
image_db.image_tags
image_db.image_elements
image_db.image_annotations
image_db.image_embeddings
image_db.image_sources
image_db.asset_collections
image_db.usage_records
```

图数据库建议关系：

```text
Image -> Element
Element -> Discipline
Element -> Alias
Element -> VisualStyle
Image -> SourceDocument
Image -> Project
Element -> CommonLayout
```

图片库不负责：

- 不负责理解客户完整需求。
- 不负责 LLM 绘图流程编排。
- 不负责最终项目交付。

## 6. 科研绘图应用平台

应用平台是最终使用系统，也是客户价值体现的位置。

职责：

- 接收客户绘图需求。
- 从文本库获取知识、术语、上下文和证据。
- 从图片库获取图元、参考图、素材和元素关系。
- 调用 LLM 生成 AI 绘图流程。
- 做元素匹配、空间构图、生成图。
- 支持图像修改、重新生成、版本对比和导出。
- 保存项目、需求、workflow、生成图和导出记录。

建议逻辑表：

```text
app_db.projects
app_db.drawing_requests
app_db.workflows
app_db.workflow_elements
app_db.workflow_relations
app_db.generated_figures
app_db.figure_versions
app_db.exports
app_db.app_runs
```

应用平台不应该继续承担：

- 文本条目维护。
- 图片素材入库。
- 大规模标签管理。
- 图数据库关系维护。

应用平台最多展示：

- 本次用了哪些文本证据。
- 本次用了哪些图片素材。
- 本次命中了哪些元素。
- 本次生成图有哪些版本。

## 7. 页面拆分建议

第一阶段建议从当前工作台拆成：

```text
科研绘图平台
├─ 仪表盘
├─ 文本库
├─ 图片库
├─ 应用平台
│  ├─ 项目
│  ├─ 需求输入
│  ├─ AI 绘图流程
│  ├─ 生成图
│  └─ 导出
└─ 设置
```

其中“生成图”应作为应用平台里的核心板块。

生成图板块应该支持：

- 查看当前生成结果。
- 重新生成。
- 局部修改。
- 版本对比。
- 下载 SVG / PNG。
- 查看质量检查结果。
- 查看引用的文本和图片素材。

## 8. 检索策略

文本检索不依赖 MySQL 实例数量，而依赖：

- 文本切片质量。
- 术语和别名体系。
- Embedding 模型。
- 向量索引。
- GraphRAG 实体关系。
- 召回和重排序策略。

图片检索不依赖 MySQL 实例数量，而依赖：

- 图片标签质量。
- 元素标注质量。
- 图片 Embedding。
- 元素关系图。
- 文件路径和元数据一致性。
- 相似图召回和过滤规则。

应用平台检索建议：

```text
客户需求
  ↓
术语识别
  ↓
文本库召回
  ↓
图片库召回
  ↓
元素资产匹配
  ↓
综合排序
  ↓
进入绘图流程
```

## 9. 阶段路线

第一阶段：逻辑拆分。

- 明确 `text_db`、`image_db`、`app_db`。
- 页面上区分文本库、图片库、应用平台。
- 应用平台只读取文本库和图片库，不再承担资产维护。

第一阶段同时采用轻量模型策略：

- 先走通完整业务流程，而不是先追求最大模型效果。
- 先部署本地小模型，例如 `qwen2.5:3b`、`qwen3:4b` 或同级别模型。
- 优先验证 RAG、文档处理、图片资产匹配和生成图链路是否闭环。
- 暂不引入复杂多云模型调度、GPU 队列和大模型部署。

第二阶段：数据结构迁移。

- 把当前知识条目归入 `text_db`。
- 把 Bioicons、本地图元和图片元数据归入 `image_db`。
- 把项目、workflow、生成图归入 `app_db`。

第三阶段：服务层拆分。

```text
text_library_service
image_library_service
drawing_application_service
workflow_service
figure_generation_service
export_service
```

第四阶段：独立平台化。

- 文本库可以成为独立管理站点。
- 图片库可以成为独立管理站点。
- 科研绘图应用平台成为最终用户入口。

第五阶段：模型与机器升级。

- 当文本库、图片库和生成图链路都跑通，并且数据量明显变大后，再迁移到更强机器，例如 305。
- 迁移后再评估更大的 Qwen、视觉模型、Embedding 模型和图像反向解析模型。
- 大模型升级应通过模型中心配置完成，避免业务代码绑定某一个模型。

## 10. 当前结论

当前推荐方案：

```text
一个 MySQL 实例
├─ text_db
├─ image_db
└─ app_db
```

系统职责：

```text
文本库负责知识
图片库负责素材
应用平台负责生成
```

下一步不建议马上大规模改代码。应先基于本设计确认页面结构、数据表边界和迁移顺序，然后再制定实现计划。

模型路线：

```text
先走通流程
  ↓
先部署小模型
  ↓
验证 RAG / 文档 / 图片 / 生成图链路
  ↓
数据量变大后
  ↓
再上更强机器，例如 305
  ↓
再换更大的模型
```
