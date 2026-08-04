# 个人健康管理助手

结合 **RAG（检索增强生成）** 与 **多 Agent 协作** 的 AI 健康咨询系统，用于展示 AI 工程能力。

> **免责声明**：本系统仅供健康信息参考，不构成医疗建议。如有特殊健康状况，请咨询专业医生或注册营养师。

## 功能特性

- **5 Agent 协作**：规划 → 检索 → 计算 → 生成 → 评审（支持评审失败循环修正）
- **RAG 私有知识库**：膳食指南、运动文献、营养成分表
- **确定性营养计算**：BMI、TDEE、蛋白质/宏量营养素（Python 工具，非 LLM 估算）
- **双 Provider 架构**：DeepSeek（LLM）+ DashScope / 本地 bge-m3（Embedding）
- **Streamlit 三 Tab UI**：用户档案、对话咨询、知识库管理

## 技术栈

| 组件 | 选型 |
|------|------|
| Agent 编排 | LangGraph 1.2.x + langchain-core 1.4.x |
| 向量数据库 | Chroma 1.x |
| LLM | DeepSeek V4 Flash（OpenAI 兼容） |
| Embedding | DashScope text-embedding-v4 / BAAI/bge-m3 |
| 前端 | Streamlit |

## 快速开始

### 1. 环境准备

```bash
cd health-assistant
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env     # 编辑 API Key（无 Key 也可运行，使用规则兜底）
```

### 2. 构建知识库

```bash
python main.py ingest
# 或
python scripts/ingest_kb.py
```

### 3. 运行

```bash
# Streamlit UI（推荐 Demo）
python main.py streamlit

# CLI 调试
python main.py cli "我身高172，体重70，想增肌，每天吃多少蛋白质？"

# RAG 评估
python main.py eval
```

### 4. 测试

```bash
pytest tests/ -v
```

## 项目结构

```
health-assistant/
├── config/           # 配置与 Prompt 模板
├── src/health_assistant/
│   ├── agents/       # 5 个 Agent 模块
│   ├── graph/        # LangGraph 编排
│   ├── rag/          # RAG 管道
│   ├── tools/        # BMI/TDEE/宏量计算
│   └── services/     # 业务入口
├── app/              # Streamlit 前端
├── data/raw/         # 原始知识库
├── scripts/          # CLI 脚本
└── tests/            # 单元/集成测试
```

## 架构亮点（求职展示）

1. **RAG + Tool 分离**：数值由 Python 工具计算，LLM 负责解读与建议，评审 Agent 双重校验
2. **LangGraph 条件循环**：评审不通过自动打回 Generator 重试（最多 2 次）
3. **无 API 可运行**：Planner/Generator/Reviewer 均有规则兜底，便于本地 Demo 与 CI 测试

## 文档

- [架构说明](docs/architecture.md)
- [Agent 设计](docs/agent_design.md)
- [部署指南](docs/deployment.md)
- [面试答辩指南](docs/interview_guide.md)

## 示例 Query

**输入**：「我身高172，体重70，想增肌，每天吃多少蛋白质？」

**输出要点**：
- BMI 23.7（normal）
- 蛋白质建议 112～154 g/天（1.6～2.2 g/kg）
- 引用膳食指南与运动营养文献
- 评审通过后返回答案

## License

MIT
