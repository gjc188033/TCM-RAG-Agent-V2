<p align="center">
  <img src="AgentFace/icon/img.png" width="120" alt="Logo"/>
</p>

<h1 align="center">🏥 中医智能问诊系统 V2</h1>

<p align="center">
  <strong>Plan-Execute-Reflect ReAct Agent · 7 工具自主决策 · 辨证论治全流程</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Architecture-ReAct_Agent-ff6b6b?style=for-the-badge" alt="ReAct"/>
  <img src="https://img.shields.io/badge/Tools-7_Specialized-a855f7?style=for-the-badge" alt="Tools"/>
  <img src="https://img.shields.io/badge/Nodes-8_LangGraph-3b82f6?style=for-the-badge" alt="Nodes"/>
  <img src="https://img.shields.io/badge/Self--Reflection-Enabled-14b8a6?style=for-the-badge" alt="Reflect"/>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue?logo=python&logoColor=white" alt="Python"/>
  <img src="https://img.shields.io/badge/Vue-3.5-brightgreen?logo=vue.js&logoColor=white" alt="Vue"/>
  <img src="https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi&logoColor=white" alt="FastAPI"/>
  <img src="https://img.shields.io/badge/LangGraph-StateGraph-orange?logo=chainlink&logoColor=white" alt="LangGraph"/>
  <img src="https://img.shields.io/badge/Qwen3--Max-LLM-purple" alt="Qwen3-Max"/>
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License"/>
</p>

---

## � V2 vs V1 — 从流水线到智能体的质变

> **V1 是一条流水线，V2 是一位真正会思考的老中医。**

<table>
  <tr>
    <th width="180">维度</th>
    <th width="280">V1 (固定 Workflow)</th>
    <th width="380">V2 (ReAct Agent) 🚀</th>
  </tr>
  <tr>
    <td><b>🧠 架构模式</b></td>
    <td>固定 4 步流水线<br/><code>扩展→检索→排序→生成</code></td>
    <td><b>Plan → Execute → Reflect</b><br/>三阶段自主循环，LLM 决定每一步做什么</td>
  </tr>
  <tr>
    <td><b>⚡ 决策能力</b></td>
    <td>零决策，每次请求必经全部 4 步</td>
    <td><b>7 个工具自主选择</b>，根据认知状态动态规划路径</td>
  </tr>
  <tr>
    <td><b>🔧 工具数量</b></td>
    <td>0 个（无工具概念）</td>
    <td><b>7 个专业化工具</b>：症状提取 · 典籍检索 · 追问病人 · 辨证分析 · 鉴别诊断 · 安全检查 · 最终诊断</td>
  </tr>
  <tr>
    <td><b>📊 认知状态</b></td>
    <td>无状态，一次性处理</td>
    <td><b>结构化认知状态</b>：症状注册表 · 证候假说 · 置信度评分 · 信息缺口 · 安全标记</td>
  </tr>
  <tr>
    <td><b>☯ 中医专业度</b></td>
    <td>直接检索 + 生成</td>
    <td><b>八纲辨证 → 鉴别诊断 → 安全检查</b> 完整诊疗流程</td>
  </tr>
  <tr>
    <td><b>🪞 自我反思</b></td>
    <td>无</td>
    <td><b>Reflect 节点</b>：信息是否充分？诊断有无遗漏？需不需要回退？</td>
  </tr>
  <tr>
    <td><b>🧐 质量控制</b></td>
    <td>无</td>
    <td><b>Critique 节点</b>：诊疗方案质量评分，不通过则重新规划</td>
  </tr>
  <tr>
    <td><b>🔖 意图分类</b></td>
    <td>无，所有输入统一处理</td>
    <td><b>Triage 节点</b>：意图分类 + 紧急度评估 + 科室方向识别</td>
  </tr>
  <tr>
    <td><b>📋 LangGraph 节点</b></td>
    <td>1 个</td>
    <td><b>8 个</b>（triage · plan · execute · observe · reflect · critique · stream · ask）</td>
  </tr>
  <tr>
    <td><b>🔄 最大迭代</b></td>
    <td>1 轮（无循环）</td>
    <td><b>6 轮</b> Plan-Execute-Reflect 循环</td>
  </tr>
</table>

---

## �📖 项目简介

本项目是面向中医诊疗场景的**检索增强生成（RAG）智能问诊系统**。V2 版本从简单的 RAG 流水线升级为**具有自主决策能力的 ReAct (Reasoning + Action) 智能体**。

系统模拟资深老中医的完整诊疗思维：**望闻问切 → 辨证论治 → 安全校验 → 开方建议**，每一步都由 LLM 自主决定是否需要追问、检索典籍、进行辨证分析，还是直接给出诊疗建议。

**核心亮点：**

- 🧠 **Plan-Execute-Reflect 架构** — 三阶段循环，包含自反思和质量批评，Agent 会检查自己的诊断是否靠谱
- 🔧 **7 个专业化工具** — 从结构化症状提取到安全性检查，覆盖完整中医诊疗流程
- ☯ **辨证论治引擎** — 八纲辨证 · 脏腑辨证 · 气血辨证 · 多证候鉴别诊断
- � **结构化认知状态** — 症状带置信度评分、证候假说带证据链、信息缺口自动追踪
- �🔍 **混合检索架构** — 稠密向量 (Qwen Embedding + Milvus) + 稀疏向量 (SPLADE-v3 + Elasticsearch)
- 💬 **流式问诊体验** — SSE 实时推送，含可视化"思考过程"展示
- 📚 **典籍级知识库** — 支持按书籍选择性检索，已收录《本草纲目》《中医急症学》等典籍

---

## 🏗️ 系统架构 V2

```
┌─────────────────────────────────────────────────────────────────────┐
│                       Frontend (Vue 3 + Vite)                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ ChatView │  │  Pinia   │  │ SSE 流式  │  │  Element Plus UI  │  │
│  │ 思考可视化│  │  Store   │  │  Client   │  │ Markdown + 高亮   │  │
│  └────┬─────┘  └────┬─────┘  └─────┬─────┘  └────────────────────┘  │
│       └──────────────┴──────────────┘                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │ HTTP / SSE
┌────────────────────────────▼────────────────────────────────────────┐
│                     Backend (FastAPI :9978)                          │
│                                                                      │
│  ┌───────── ReAct Agent (Plan-Execute-Reflect) ──────────────────┐  │
│  │                                                                 │  │
│  │  🔖 Triage ──→ 📋 Plan ──→ ⚡ Execute ──→ 🪞 Reflect          │  │
│  │                   ↑                           │                 │  │
│  │                   └──── 信息不足/质量不达标 ────┘                 │  │
│  │                                                                 │  │
│  │  ⚡ Execute 可调用的 7 个工具：                                   │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │  │
│  │  │ 🔬 症状提取   │ │ 📚 典籍检索   │ │ ❓ 追问病人   │            │  │
│  │  │  结构化 + 置信度│ │ Milvus + ES  │ │ 基于信息缺口  │            │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │  │
│  │  │ ☯ 辨证分析   │ │ 🔍 鉴别诊断   │ │ 🛡️ 安全检查   │            │  │
│  │  │ 八纲/脏腑/气血│ │ 多假说排序    │ │ 禁忌 + 配伍   │            │  │
│  │  └──────────────┘ └──────────────┘ └──────────────┘            │  │
│  │  ┌──────────────┐                                               │  │
│  │  │ 📝 最终诊断   │  →  🧐 Critique 质量审核  →  ✅ 流式输出     │  │
│  │  └──────────────┘                                               │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────────────┐     │
│  │ LangGraph   │  │ Conversation │  │ Redis Chat History     │     │
│  │ 8-Node DAG  │  │   Manager    │  │  (LangChain)           │     │
│  └─────────────┘  └──────────────┘  └────────────────────────┘     │
└──────────────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
 ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
 │    Milvus    │   │Elasticsearch │   │    Redis     │
 │ Dense Vector │   │Sparse Vector │   │   Session    │
 │  (3584-dim)  │   │  (SPLADE)    │   │   Storage    │
 └──────────────┘   └──────────────┘   └──────────────┘
```

---

## 🧠 ReAct Agent 工作流程

```
病人: "我头疼发热三天了"
         │
         ▼
  ┌──────────────────┐
  │  � Triage       │  → 意图: 问诊 | 科室: 内科 | 紧急度: medium
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  📋 Plan (第1轮)  │  → 计划: [extract_symptoms, ask_patient]
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  🔬 症状提取      │  → 头痛(0.8) + 发热(0.9) | 缺口: 部位,性质,舌象,脉象
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  ❓ 追问病人      │  → "请问头痛是什么部位？胀痛刺痛还是隐痛？有无咳嗽？"
  └────────┬─────────┘
           ▼
     ← 返回，等待病人回答 →

病人: "前额胀痛，伴咳嗽黄痰，口渴"
         │
         ▼
  ┌──────────────────┐
  │  📋 Plan (第2轮)  │  → 计划: [extract_symptoms, tcm_pattern, search_books, final_diagnosis]
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  🔬 症状提取      │  → 前额胀痛 + 咳嗽 + 黄痰 + 口渴 (共6个症状)
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  ☯ 辨证分析      │  → 八纲: 阳/表/热/实 | 证候: 风热犯肺(0.85)
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  📚 典籍检索      │  → Dense + Sparse 混合检索 → Rerank → 5篇文献
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  🪞 自我反思      │  → 信息充分 (sufficient) | 置信度 0.85 | 可以诊断
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  🛡️ 安全检查      │  → 通过 ✓ (无特殊禁忌)
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  🧐 质量审核      │  → 评分: 8.5/10 | 通过 ✓
  └────────┬─────────┘
           ▼
  ┌──────────────────┐
  │  ✅ 流式输出      │  → "根据辨证分析，您属于风热犯肺证..."
  └──────────────────┘
```

---

## 🔬 核心技术细节

### ReAct Agent 认知状态

Agent 在运行过程中维护一套**结构化认知状态**，驱动自主决策：

| 状态域 | 结构 | 作用 |
|--------|------|------|
| `symptoms` | `[{name, location, nature, duration, severity, confidence, related_tcm}]` | 结构化症状注册表，每个症状带置信度 |
| `tcm_patterns` | `[{pattern_name, confidence, supporting_evidence, contradicting_evidence}]` | 证候假说列表，含支持/矛盾证据链 |
| `diagnosis_hypotheses` | `[{diagnosis, probability, key_supporting, key_against}]` | 鉴别诊断排名，按概率排序 |
| `information_gaps` | `["舌象", "脉象", ...]` | 信息缺口追踪，驱动追问逻辑 |
| `safety_flags` | `[{level, description, suggestion}]` | 安全标记（禁忌、配伍、人群） |
| `confidence_score` | `float (0~1)` | 整体诊断置信度，>0.7 才允许出诊断 |

### 7 个专业化工具

| # | 工具 | 技术实现 | 智能体何时调用 |
|---|------|----------|---------------|
| 1 | 🔬 `extract_symptoms` | LLM 结构化提取 + 置信度标注 | 每轮对话开始，从自然语言提取症状 |
| 2 | 📚 `search_books` | Milvus Dense + ES Sparse + LLM Rerank | 需要查阅典籍验证假说、找方剂 |
| 3 | ❓ `ask_patient` | 基于信息缺口自动生成追问 | 症状不足、缺少关键信息时 |
| 4 | ☯ `tcm_pattern` | LLM 八纲辨证 + 脏腑辨证 + 气血辨证 | 症状≥3个，可以开始辨证 |
| 5 | 🔍 `differential_dx` | LLM 多假说对比分析 | 有多个候选证候需要鉴别 |
| 6 | 🛡️ `check_safety` | LLM 药物安全检查（十八反、十九畏等） | 给出治疗建议前的安全门控 |
| 7 | 📝 `final_diagnosis` | RAG Chain 流式生成 + 辨证/安全增强上下文 | 信息充足、置信度高、安全通过后 |

### 混合向量检索

```
用户查询
    │
    ├──→ Qwen Embedding (3584维) ──→ Milvus (IP + IVF_FLAT, nprobe=10)
    │                                       ↓
    │                                 稠密向量 Top-K 结果
    │
    └──→ SPLADE-v3 (稀疏向量) ──→ Elasticsearch (BM25 + Sparse Term)
                                        ↓
                                  稀疏向量 Top-K 结果
                                        ↓
                              ────── 结果合并去重 ──────
                                        ↓
                              LLM Reranking → Top-N 文档
```

### 会话管理

- Redis **Hash** 存储会话元数据（标题、时间、消息数）
- Redis **ZSet** 有序集合管理会话列表（按创建时间排序）
- LangChain `RedisChatMessageHistory` 管理消息历史
- 首条消息自动生成会话标题（截取前 30 字符）

### 流式通信

- 后端使用 FastAPI `StreamingResponse` + SSE（Server-Sent Events）协议
- 前端使用原生 `Fetch API` + `ReadableStream` 解析 SSE 数据
- 支持事件类型：`thinking_step`（思考进度）、`thinking_update`（步骤更新）、`thinking_complete`（思考完成）、`content`（答案内容）、`complete`（完成标记）

---

## 📁 项目结构

```
TCM-RAG-Agent-V2/
│
├── IntelligentAgent/                    # 🐍 Python 后端
│   ├── main.py                          # FastAPI 入口 + API 路由
│   └── BaseOne/
│       ├── Agent/
│       │   ├── Rag/
│       │   │   ├── ReActAgent.py       # ★★ V2 新增：Plan-Execute-Reflect ReAct Agent 核心
│       │   │   ├── RagAgent.py         # RAG Agent 入口，委托给 ReActAgent
│       │   │   ├── MilvusWoker.py      # Milvus 稠密向量检索
│       │   │   ├── ElasticsearchWoker.py  # ES 稀疏向量检索
│       │   │   ├── embeddings.py       # Qwen + SPLADE 嵌入模型
│       │   │   ├── config.py           # 数据库连接配置
│       │   │   └── models/             # 本地模型文件
│       │   ├── BaseAsk.py              # 基础问答 Agent
│       │   └── StreamBase.py           # 流式问答 Agent
│       ├── API/Request/                # Pydantic 请求模型
│       ├── Memorys/
│       │   └── ConversationManager.py  # Redis 会话管理器
│       ├── Prompts/
│       │   └── MyPrompt.py            # ★★ V2 扩展：9 个专业 Prompt 模板
│       └── utils/
│           ├── llms.py                 # LLM 初始化 (Qwen3-Max)
│           └── config.example.py       # API Key 配置模板
│
├── AgentFace/                           # 🖥️ Vue 3 前端
│   ├── src/
│   │   ├── App.vue                     # 主应用 + 导航
│   │   ├── components/Views/
│   │   │   └── ChatView.vue            # ★ 聊天界面 (思考过程可视化)
│   │   ├── api/index.js                # API 封装 + SSE 流式通信
│   │   └── store/conversation.js       # Pinia 全局状态管理
│   ├── package.json
│   └── vite.config.js
│
├── requirements.txt                     # Python 依赖
└── README.md
```

---

## 🛠️ 技术栈

### 后端

| 组件 | 技术 | 用途 |
|------|------|------|
| Web 框架 | **FastAPI** | 异步 API 服务，原生 StreamingResponse |
| LLM | **Qwen3-Max** (DashScope) | ReAct 推理 · 辨证分析 · 鉴别诊断 · 安全检查 · 答案生成 |
| Agent 框架 | **LangGraph** (StateGraph) | 8 节点有向图，条件路由，Plan-Execute-Reflect 循环 |
| 提示工程 | **LangChain** (ChatPromptTemplate) | 9 个角色化 Prompt 模板（Triage/Plan/辨证/反思/批评等） |
| 稠密嵌入 | **Qwen Embedding** (本地) | 3584 维文本向量，CLS pooling + L2 norm |
| 稀疏嵌入 | **SPLADE-v3** (本地) | 稀疏激活向量，log(1+ReLU) + Max pooling |
| 向量数据库 | **Milvus** | IVF_FLAT 索引，IP 度量 |
| 搜索引擎 | **Elasticsearch** | 稀疏向量 Term 查询 + BM25 |
| 会话存储 | **Redis** | Hash + ZSet + LangChain ChatHistory |

### 前端

| 组件 | 技术 | 用途 |
|------|------|------|
| 框架 | **Vue 3** (Composition API) | 响应式 UI |
| 构建 | **Vite 7** | 快速热更新开发 |
| 状态管理 | **Pinia** | 会话 + 消息全局状态 |
| UI 组件 | **Element Plus** | 通知、对话框等 |
| 流式通信 | **Fetch API** + ReadableStream | SSE 实时数据解析 |
| 渲染 | **Marked** + Highlight.js | Markdown 渲染 + 代码高亮 |

---

## 🚀 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Redis 服务
- Milvus 2.x 服务
- Elasticsearch 8.x 服务

### 1. 克隆仓库

```bash
git clone https://github.com/your-username/TCM-RAG-Agent-V2.git
cd TCM-RAG-Agent-V2
```

### 2. 下载模型

本项目使用以下本地模型，请下载至 `IntelligentAgent/BaseOne/Agent/Rag/models/` 目录：

| 模型 | 用途 | 下载方式 |
|------|------|----------|
| **Qwen Embedding** | 稠密向量嵌入 | 从 [ModelScope](https://modelscope.cn/) 或 [HuggingFace](https://huggingface.co/) 下载至 `models/Qwen/` |
| **SPLADE-v3** | 稀疏向量嵌入 | 从 [HuggingFace](https://huggingface.co/naver/splade-v3) 下载至 `models/splade-v3/` |

### 3. 后端部署

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置 API Key
cp IntelligentAgent/BaseOne/utils/config.example.py IntelligentAgent/BaseOne/utils/config.py
# 编辑 config.py，填入你的阿里云 DashScope API Key

# 修改数据库连接配置（按需）
# 编辑 IntelligentAgent/BaseOne/Agent/Rag/config.py

# 启动后端服务
python -m IntelligentAgent.main
# 服务运行在 http://0.0.0.0:9978
```

### 4. 前端部署

```bash
cd AgentFace

# 安装依赖
npm install

# 开发模式启动
npm run dev
# 前端运行在 http://localhost:5173

# 生产构建
npm run build
```

### 5. 基础设施配置

确保以下服务已部署并可访问：

```yaml
Redis:         redis://your-host:6379
Milvus:        http://your-host:19530
Elasticsearch: http://your-host:9200
```

在 `IntelligentAgent/BaseOne/Agent/Rag/config.py` 中更新对应地址。

---

## 💡 API 接口

| 端点 | 方法 | 说明 |
|------|------|------|
| `/model_status` | GET | 获取 RAG 模型加载状态 |
| `/booksname` | POST | 获取可选书籍列表 |
| `/conversations` | POST | 创建新会话 |
| `/conversations` | GET | 获取会话列表（分页） |
| `/conversations/{id}` | GET | 获取会话详情 |
| `/conversations/{id}` | DELETE | 删除会话 |
| `/conversations/{id}/title` | PUT | 更新会话标题 |
| `/conversations/{id}/messages` | GET | 获取历史消息 |
| `/conversations/{id}/messages/ragstream` | POST | **核心：ReAct Agent 流式问答** |

### 流式问答请求示例

```bash
curl -X POST http://localhost:9978/conversations/{session_id}/messages/ragstream \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "session_xxx",
    "admin": "AI助手",
    "content": "头痛发热三天，伴有咳嗽，该怎么治疗？",
    "books": ["本草纲目", "中医急症学"]
  }'
```

响应为 SSE 流，包含以下事件类型：

```
data: {"thinking_step": {"icon": "�", "title": "导诊分类", "details": "意图: 问诊 | 科室: 内科"}}
data: {"thinking_step": {"icon": "📋", "title": "制定诊疗计划", "details": "计划: extract → tcm → search → diagnose"}}
data: {"thinking_step": {"icon": "🔬", "title": "症状结构化提取", "details": "提取到 4 个症状"}}
data: {"thinking_step": {"icon": "☯",  "title": "辨证论治分析", "details": "主要证候: 风热犯肺(85%)"}}
data: {"thinking_step": {"icon": "📚", "title": "检索中医典籍", "details": "检索到 12 条相关文档"}}
data: {"thinking_step": {"icon": "🪞", "title": "自我反思", "details": "信息充分, 置信度 0.85"}}
data: {"thinking_step": {"icon": "🛡️", "title": "安全性检查", "details": "安全检查通过 ✓"}}
data: {"thinking_step": {"icon": "🧐", "title": "质量审核", "details": "评分: 8.5/10 通过 ✓"}}
data: {"thinking_complete": true, "thinking_steps": [...]}
data: {"content": "根据", "status": "generating"}
data: {"content": "辨证分析", "status": "generating"}
...
data: {"content": "", "status": "complete"}
```

---

## 📄 License

MIT License
