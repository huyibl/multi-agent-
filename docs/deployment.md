# 部署指南

## 本地开发（Windows）

### 前置条件

- Python 3.10+
- 8GB+ RAM（本地 Embedding 需要）

### 步骤

```powershell
cd health-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

编辑 `.env`：

```env
DEEPSEEK_API_KEY=sk-your-key
DASHSCOPE_API_KEY=sk-your-key
EMBEDDING_PROVIDER=local   # 或 dashscope
```

### 构建知识库

```powershell
python main.py ingest
```

### 启动 UI

```powershell
python main.py streamlit
```

浏览器访问 `http://localhost:8501`

## 环境变量说明

| 变量 | 必填 | 说明 |
|------|------|------|
| DEEPSEEK_API_KEY | 否 | LLM API，无则使用规则兜底 |
| DASHSCOPE_API_KEY | 否 | Embedding API，无则使用 bge-m3 |
| EMBEDDING_PROVIDER | 否 | `local` 或 `dashscope` |
| CHROMA_PERSIST_DIR | 否 | 向量库路径，默认 `./data/chroma` |

## LangSmith 追踪（可选）

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=ls-xxx
LANGCHAIN_PROJECT=health-assistant
```

## Docker（可选扩展）

当前 MVP 以本地 Streamlit 为主。生产部署可考虑：

- FastAPI 包装 `ChatService`
- Docker Compose：app + Chroma + PostgreSQL (PGVector)

## 常见问题

**Q: 首次 ingest 很慢？**  
A: 本地 bge-m3 首次需下载模型（约 2GB），可设 `EMBEDDING_PROVIDER=dashscope` 加速。

**Q: Chroma 目录过大？**  
A: `data/chroma/` 已在 `.gitignore`，可删除后重新 ingest。

**Q: Windows 中文路径问题？**  
A: 建议项目放在英文路径下，如 `D:\projects\health-assistant`。
