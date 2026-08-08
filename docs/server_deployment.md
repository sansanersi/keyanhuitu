# 服务器部署前检查

这份文档用于把当前科研绘图工作台部署到测试服务器或演示服务器。现阶段建议定位为“内测/演示版”，先跑通 RAG、文档处理、图片库、绘图流程和 LLM 编排链路，再进入生产化改造。

## 当前部署结论

当前项目可以部署到服务器，但不建议直接作为生产系统开放给多人使用。

已具备：

- Flask Web 应用入口。
- 文本库、图片库、应用平台三个服务边界。
- 本地 SQLite 运行库。
- Ollama 本地模型接入。
- 可配置 Web 监听地址和端口。
- 服务器环境变量模板、启动脚本和健康检查脚本。

仍需生产化补齐：

- MySQL 真实迁移和数据同步脚本。
- 图片资产对象存储或规范化文件目录。
- 用户登录、权限和审计。
- 进程守护、日志轮转、备份和监控。
- 反向代理 HTTPS。

## 推荐服务器形态

第一阶段建议使用一台小服务器或 Windows/Linux 测试机：

```text
浏览器
  ↓
Nginx 或内网访问
  ↓
Flask / Waitress
  ↓
SQLite 运行库 + 本地文件目录
  ↓
Ollama 小模型
```

数据量变大后再演进为：

```text
应用平台
  ↓
文本库服务 / 图片库服务 / 绘图应用服务
  ↓
MySQL(text_db, image_db, app_db) + 向量库 + 图数据库 + 对象存储
  ↓
独立 LLM 服务或更强本地模型机器
```

## 环境变量

复制模板：

```powershell
Copy-Item .env.server.example .env
```

重点配置：

| 变量 | 说明 |
|------|------|
| `SCI_WEB_HOST` | 服务器监听地址，内网测试可用 `0.0.0.0` |
| `SCI_WEB_PORT` | Web 端口，默认 `5000` |
| `SCI_WEBAPP_DB_PATH` | SQLite 运行库路径，必须纳入备份 |
| `OLLAMA_BASE_URL` | Ollama 服务地址 |
| `OLLAMA_DEFAULT_MODEL` | 当前建议 `qwen2.5:0.5b` 先轻量跑通 |
| `BIOICONS_ROOT` | Bioicons 或本地图元目录 |

## 启动方式

Windows PowerShell：

```powershell
.\scripts\start_server.ps1 -HostAddress 0.0.0.0 -Port 5000 -BioiconsRoot D:\sci-illust-runtime\bioicons
```

如果只在本机验证：

```powershell
.\scripts\start_server.ps1
```

## 健康检查

Web 和 Ollama 都启动后执行：

```powershell
.\scripts\health_check.ps1 -BaseUrl http://127.0.0.1:5000 -OllamaUrl http://127.0.0.1:11434
```

检查项：

- 首页是否可访问。
- 仪表盘接口是否可访问。
- 文本库仪表盘是否可访问。
- 图片库仪表盘是否可访问。
- 绘图模型接口是否可访问。
- Ollama 服务是否可访问。

## 数据备份

上线前至少备份这些路径：

```text
sci-illust-system/web_app/data/knowledge.db
SCI_WEBAPP_DB_PATH 指向的运行库
BIOICONS_ROOT 指向的图片素材目录
后续 image_db 对应的图片文件目录
```

注意：`knowledge.db` 是运行态数据库，不应该提交到 Git。

## 上线前必须确认

- `python -m unittest discover -s tests -p "test_*.py" -v` 通过。
- `scripts/health_check.ps1` 通过。
- Ollama 至少有一个轻量模型，例如 `qwen2.5:0.5b`。
- 服务器防火墙只开放必要端口。
- `.env` 没有提交到 Git。
- 运行态数据库和图片目录有备份策略。
