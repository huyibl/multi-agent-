# 部署指南

## 本地

```powershell
cd health-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements-local.txt
copy .env.example .env
# 填写 DEEPSEEK_API_KEY、DASHSCOPE_API_KEY；EMBEDDING_PROVIDER=dashscope
python main.py ingest
python main.py streamlit
```

访问 `http://localhost:8501`。管理员入库：`http://localhost:8501/?admin=1`。

## Streamlit Cloud

1. 仓库含 `runtime.txt`（Python 3.11）与 `pysqlite3-binary`（修复 Cloud SQLite）
2. Main file：`app/streamlit_app.py`
3. Secrets（参考 `.streamlit/secrets.toml.example`）：

```toml
DEEPSEEK_API_KEY = "sk-xxx"
DASHSCOPE_API_KEY = "sk-xxx"
EMBEDDING_PROVIDER = "dashscope"
PLANNER_USE_LLM = "auto"
REVIEWER_USE_LLM = "auto"
ANONYMIZED_TELEMETRY = "False"
```

**不要**在 Cloud 使用 `EMBEDDING_PROVIDER=local`（需下载 bge-m3）。

Cloud 使用 **Chroma Ephemeral（内存）**，但 **首次打开会自动从 `data/raw` 入库**（需配置 `DASHSCOPE_API_KEY`），访客无需操作。进程 Reboot 后会再自动建库一次。`?admin=1` 仅供强制重建。本地仍用 Persistent + `data/chroma/`。

本地无 `secrets.toml` 时，`config/bootstrap.py` 会跳过 Secrets，继续读 `.env`。

## 环境变量

| 变量 | 说明 |
|------|------|
| `DEEPSEEK_API_KEY` | LLM；空则规则/模板兜底 |
| `DASHSCOPE_API_KEY` | Embedding（Cloud 必填） |
| `EMBEDDING_PROVIDER` | `dashscope` / `local` |
| `PLANNER_USE_LLM` / `REVIEWER_USE_LLM` | `auto` \| `always` \| `never` |

## 评测

```bash
python main.py eval-suite          # 50 检索 + 8 RAGAS-lite
python scripts/run_eval_suite.py --skip-llm   # 仅检索
python main.py benchmark           # E2E 对比
```

## 常见问题

| 现象 | 处理 |
|------|------|
| SecretsNotFound 本地报错 | 已修复：无 toml 时跳过；请用最新 `bootstrap.py` |
| `default_tenant` / Chroma ValueError | 确认 `runtime.txt`=3.11、已装 `pysqlite3-binary`；Reboot 后 `?admin=1` 重建 |
| Chroma panic（本地） | `python main.py ingest` 重建 |
| streamlit/starlette 冲突 | 保持 `streamlit<1.45`、`fastapi==0.115.9` |
