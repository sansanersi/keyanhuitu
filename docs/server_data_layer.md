# 服务器版 v1 数据层设计

当前目标是把科研绘图工作台从本机运行形态推进到服务器正式系统形态。第一阶段不直接替换现有 SQLite 读写逻辑，而是先建立 MySQL 三逻辑库的稳定边界和初始化 SQL。

## 数据库拆分

采用一个 MySQL 实例，三个逻辑库：

| 逻辑库 | 职责 |
|------|------|
| `text_db` | 文本库：术语、论文、图注、文档切块、RAG 输入 |
| `image_db` | 图片库：图元、Bioicons、本地素材、别名、图元关系 |
| `app_db` | 应用平台：绘图需求、workflow、生成图、模型配置 |

这个拆分不会影响检索效果本身。检索效果主要取决于数据质量、切块、Embedding、图元匹配和召回排序。三库拆分的价值是让数据职责清楚，后面接向量库、图数据库、对象存储时不会互相污染。

## 表结构

当前 schema 由代码生成：

```powershell
python scripts/generate_mysql_schema.py --output build/mysql_schema.sql
```

核心表：

| 逻辑库 | 表 | 说明 |
|------|------|------|
| `text_db` | `terms` | 专业术语、中文名、英文名、标签、描述 |
| `text_db` | `documents` | 上传文档、内容、文件路径、向量化状态 |
| `text_db` | `document_chunks` | 文档切块和 embedding 引用 |
| `image_db` | `image_assets` | 可绘制图元、SVG、本地素材、Bioicons |
| `image_db` | `asset_aliases` | 图元中文/英文别名 |
| `image_db` | `asset_relations` | 图元关系，后续可同步到图数据库 |
| `app_db` | `drawing_requests` | 用户绘图需求 |
| `app_db` | `workflows` | AI 绘图流程 JSON |
| `app_db` | `generated_figures` | 生成图输出记录 |
| `app_db` | `model_configs` | Ollama / API 模型配置 |

## 当前状态

已完成：

- MySQL 三逻辑库名称来自 `.env.server.example` / 环境变量。
- 可生成 MySQL 初始化 SQL。
- 自动化测试覆盖三库、核心表和脚本输出。
- 现有 SQLite 运行逻辑保持兼容，不会破坏当前系统。

未完成：

- SQLite 数据导出到 MySQL。
- Web 服务实际切换到 MySQL Repository。
- 文档切块向量库同步。
- 图片文件对象存储和图数据库同步。

## 下一阶段

建议下一阶段做 Repository 抽象：

```text
现有服务层
  ↓
Repository 接口
  ↓
SQLiteRepository / MySQLRepository
```

这样可以先让测试继续跑 SQLite，再逐步把服务器环境切换到 MySQL。
