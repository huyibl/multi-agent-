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

1. 提交预构建 `data/chroma/`（约 1–2MB）
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
| Chroma panic | `python main.py ingest` 重建（或带 reset 脚本） |
| streamlit/starlette 冲突 | 保持 `streamlit<1.45`、`fastapi==0.115.9` |
