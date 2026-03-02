# 🚢 船代智能问答助手 (Ship Agency Intelligent Q&A Assistant)

基于 LangGraph + ReAct Agent 的航运船代领域智能问答系统，提供法规检索、费用计算、合规校验等专业服务。

---

## 🏗️ 系统架构

```
用户提问 → FastAPI(SSE) → ReAct Agent → Plan → Execute → Reflect → 流式回答
                                          ↓
                              ┌──────────────────────────────────────┐
                              │  7 大专业工具                        │
                              │  ① 意图分类 ② 实体提取 ③ 规章检索   │
                              │  ④ 追问用户 ⑤ 术语查询 ⑥ SQL查询    │
                              │  ⑦ 合规校验                         │
                              └──────────────────────────────────────┘
                                          ↓
                              ┌──────────────────────────────────────┐
                              │  双索引混合检索 (ES BM25 + bge-m3)   │
                              │  PostgreSQL 术语同义归一              │
                              │  LLM Reranking + 质量审核            │
                              └──────────────────────────────────────┘
```

## 🧰 技术栈

| 组件 | 技术 |
|------|------|
| **后端框架** | FastAPI + Uvicorn |
| **智能体** | LangGraph + ReAct (Plan-Execute-Reflect) |
| **LLM** | OpenAI 兼容接口 (可替换) |
| **稠密向量** | bge-m3 (1024维) |
| **稀疏检索** | Elasticsearch BM25 + SPLADE |
| **术语库** | PostgreSQL + pg_trgm |
| **会话管理** | Redis |
| **前端** | Vue 3 + Element Plus |
| **通信** | SSE (Server-Sent Events) |

## 📁 项目结构

```
Ship/
├── ShipServer/                          # 后端服务
│   ├── server.py                        # FastAPI 入口
│   └── core/
│       ├── templates/
│       │   └── prompt_registry.py       # 9 个领域 Prompt 模板
│       ├── agents/
│       │   ├── simple_qa.py             # 简单问答
│       │   ├── stream_handler.py        # 流式基类
│       │   └── retrieval/
│       │       ├── reasoning_engine.py  # ReAct Agent 核心（7工具）
│       │       ├── retrieval_orchestrator.py  # RAG 编排器
│       │       ├── es_client.py         # ES 检索客户端
│       │       ├── pg_terminology.py    # PostgreSQL 术语库
│       │       ├── vector_encoder.py    # bge-m3 嵌入封装
│       │       ├── db_settings.py       # 数据库配置
│       │       └── models/              # 模型文件
│       ├── session/
│       │   └── session_store.py         # Redis 会话管理
│       ├── schemas/
│       │   └── request/
│       │       ├── query_schema.py      # 请求结构
│       │       └── conversation_schema.py
│       └── foundation/
│           ├── llm_client.py            # LLM 客户端
│           └── api_keys.example.py      # API 密钥模板
├── ShipWeb/                             # 前端 (Vue 3)
│   └── src/
│       ├── App.vue                      # 深蓝航运主题
│       ├── components/Views/ChatView.vue
│       ├── api/index.js
│       └── store/conversation.js
├── requirements.txt
├── 技术方案.md
└── README.md
```

## 🚀 快速开始

### 环境要求
- Python 3.10+
- Node.js 16+
- Elasticsearch 8.x
- PostgreSQL 14+
- Redis 6+

### 后端启动

```bash
cd ShipServer

# 复制 API 密钥配置
cp core/foundation/api_keys.example.py core/foundation/api_keys.py
# 编辑 api_keys.py 填入实际的 API Key

pip install -r ../requirements.txt

# 将 bge-m3 和 bge-reranker 模型放入 core/agents/retrieval/models/ 目录

python server.py
# 服务运行在 http://localhost:9978
```

### 前端启动

```bash
cd ShipWeb
npm install
npm run dev
```

### 术语库初始化

```python
from core.agents.retrieval.pg_terminology import TerminologyDB
db = TerminologyDB()
db.create_tables()
```

## 🤖 ReAct Agent 工具说明

| 工具 | 功能 |
|------|------|
| `extract_entities` | 从用户问题中提取船名、港口、货物类型等结构化实体 |
| `search_regulations` | ES 混合检索（BM25 + Dense）+ LLM Reranking |
| `ask_user` | 基于缺失约束生成专业追问 |
| `query_terminology` | 术语同义归一、编码映射、关联规则校验 |
| `execute_sql` | 多源证据鉴别排名 |
| `check_compliance` | 业务方案合规性校验 |
| `generate_answer` | 基于全部上下文生成最终专业解答 |

## 📜 License

本项目仅供学习研究使用。
