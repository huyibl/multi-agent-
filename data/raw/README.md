# 健康知识库原始数据

本目录存放 RAG 知识库的原始文档。**均为公开资料摘要或自行整理的学习笔记，非完整版权文档。**

## 目录说明

| 子目录 | 内容类型 | doc_type |
|--------|----------|----------|
| `dietary_guidelines/` | 膳食指南、DRIs 摘要 | `dietary_guideline` |
| `exercise_literature/` | 运动营养、训练文献摘要 | `exercise` |
| `nutrition_tables/` | 营养成分表、推荐摄入量 CSV | `nutrition_table` |

## 数据来源说明

- 中国居民膳食指南相关：公开政策摘要与通用营养学共识
- ISSN 相关：国际运动营养学会公开立场声明要点整理
- 营养表：常见食物公开营养数据整理

## 入库

```bash
python main.py ingest
```

## 免责声明

仅供 RAG 检索演示与健康信息参考，不构成医疗建议。
