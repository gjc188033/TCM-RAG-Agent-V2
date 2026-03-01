"""
高级 ReAct Agent — Plan-Execute-Reflect 架构

中医智能问诊系统核心智能体。采用三阶段循环架构：
  Plan（规划诊疗路径）→ Execute（依次执行工具）→ Reflect（自我反思）
  
特性：
  - 7 个专业化工具（症状提取、典籍检索、追问、辨证、鉴别、安全检查、最终诊断）
  - 结构化认知状态（症状注册表、证候假说、置信度、信息缺口追踪）
  - 自反思 / 质量批评循环
  - 置信度驱动的自动路由
  - 完整 SSE 事件兼容

Author: TCM-RAG-Agent-V2
"""

from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage
from BaseOne.utils.llms import ChatBase
from BaseOne.Prompts.MyPrompt import (
    rag_system_prompt,
    rag_human_prompt,
    triage_prompt_template,
    plan_prompt_template,
    extract_symptoms_prompt_template,
    tcm_pattern_prompt_template,
    differential_diagnosis_prompt_template,
    safety_check_prompt_template,
    reflect_prompt_template,
    critique_prompt_template,
    react_system_template,
    react_human_template,
)
from .MilvusWoker import MilvusDB
from .ElasticsearchWoker import ElasticsearchDB
from .config import MILVUS_URI, MILVUS_USER, MILVUS_PASSWORD, MILVUS_COLLECTION
from typing import TypedDict, List, Dict, Any, AsyncIterator, Optional
import asyncio
import json
import re
import time


# ══════════════════════════════════════════════════════════════════
#  1. Agent State — 结构化认知状态
# ══════════════════════════════════════════════════════════════════

class AgentState(TypedDict):
    """高级 ReAct Agent 的认知状态"""

    # ── 输入 ──
    query: str                      # 用户原始问题
    admin: str                      # 角色标识
    chat_history: list              # 聊天历史
    books: list                     # 用户选择的书籍

    # ── 诊疗认知 ──
    triage_result: dict             # 意图分类结果 {"intent","urgency","department","brief_summary"}

    symptoms: list                  # 结构化症状表
                                    # [{"name","location","nature","duration","severity","confidence","related_tcm"}]

    tcm_patterns: list              # 证候假说
                                    # [{"pattern_name","confidence","supporting_evidence","contradicting_evidence","affected_organs","pathogenesis"}]

    diagnosis_hypotheses: list      # 鉴别诊断排名
                                    # [{"diagnosis","probability","key_supporting","key_against","distinguishing_points"}]

    information_gaps: list          # 信息缺口 ["舌象","脉象",...]

    safety_flags: list              # 安全标记
                                    # [{"level","description","suggestion"}]

    primary_pattern: str            # 主要证候名称
    ba_gang: dict                   # 八纲辨证 {"yin_yang","biao_li","han_re","xu_shi"}

    # ── 循环控制 ──
    diagnostic_plan: list           # 当前诊疗计划 ["extract_symptoms","search_books",...]
    plan_step_index: int            # 当前执行到第几步
    scratchpad: list                # 完整推理记录
    retrieved_docs: list            # 已检索文档（累积）
    current_iteration: int          # 当前迭代轮次
    max_iterations: int             # 最大迭代次数（默认6）
    executed_tools: list            # 已执行的工具列表

    # ── 当前决策 ──
    thought: str
    action: str
    action_input: dict
    confidence_score: float         # 整体诊断置信度 (0~1)

    # ── 输出 ──
    final_response: str


# ══════════════════════════════════════════════════════════════════
#  2. ReAct Agent 主类
# ══════════════════════════════════════════════════════════════════

class ReActAgent:
    """高级 Plan-Execute-Reflect 中医问诊智能体"""

    # 合法的 action 名称
    VALID_ACTIONS = {
        "extract_symptoms", "search_books", "ask_patient",
        "tcm_pattern", "differential_dx", "check_safety", "final_diagnosis"
    }

    def __init__(self, redis_url: str, session_id: str, milvus_client=None):
        self.session_id = session_id
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

        # ── 初始化检索客户端 ──
        try:
            self.elasticsearch_client = ElasticsearchDB()
            print("✅ [ReActAgent] Elasticsearch 初始化成功")
        except Exception as e:
            print(f"❌ [ReActAgent] Elasticsearch 初始化失败: {e}")
            self.elasticsearch_client = None

        try:
            self.milvus_client = milvus_client or MilvusDB(
                uri=MILVUS_URI, user=MILVUS_USER,
                password=MILVUS_PASSWORD, collection=MILVUS_COLLECTION
            )
            print("✅ [ReActAgent] Milvus 初始化成功")
        except Exception as e:
            print(f"❌ [ReActAgent] Milvus 初始化失败: {e}")
            self.milvus_client = None

        # RAG 回答链
        self.rag_prompt = ChatPromptTemplate.from_messages([
            rag_system_prompt, MessagesPlaceholder("history"), rag_human_prompt
        ])
        self.rag_chain = self.rag_prompt | ChatBase

    # ══════════════════════════════════════════════════════════════
    #  LLM 调用辅助
    # ══════════════════════════════════════════════════════════════

    @staticmethod
    def _call_llm(prompt_text: str) -> str:
        """同步调用 LLM 并返回文本"""
        response = ChatBase.invoke([HumanMessage(content=prompt_text)])
        return response.content

    @staticmethod
    def _parse_json_response(text: str) -> Any:
        """从 LLM 响应中提取 JSON"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith("```"):
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试匹配 {...} 或 [...]
        match = re.search(r'(\{[\s\S]*\}|\[[\s\S]*\])', text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        return None

    # ══════════════════════════════════════════════════════════════
    #  工具 1: Triage — 意图分类
    # ══════════════════════════════════════════════════════════════

    def _tool_triage(self, state: AgentState) -> dict:
        """意图分类 + 紧急度评估"""
        print("\n🔖 [Triage] 正在进行意图分类...")
        try:
            prompt = triage_prompt_template.format(
                query=state["query"],
                history=self._format_chat_history(state.get("chat_history", []))
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                print(f"  ✓ 意图: {result.get('intent')} | 紧急度: {result.get('urgency')} | 科室: {result.get('department')}")
                return {"triage_result": result}
        except Exception as e:
            print(f"  ✗ Triage 失败: {e}")

        return {"triage_result": {"intent": "问诊", "urgency": "medium", "department": "内科", "brief_summary": state["query"][:50]}}

    # ══════════════════════════════════════════════════════════════
    #  工具 2: Extract Symptoms — 结构化症状提取
    # ══════════════════════════════════════════════════════════════

    def _tool_extract_symptoms(self, state: AgentState) -> dict:
        """从自然语言中提取结构化症状"""
        print("\n🔬 [Extract Symptoms] 正在提取结构化症状...")
        try:
            existing = json.dumps(state.get("symptoms", []), ensure_ascii=False)
            prompt = extract_symptoms_prompt_template.format(
                query=state["query"],
                history=self._format_chat_history(state.get("chat_history", [])),
                existing_symptoms=existing
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                symptoms = result.get("symptoms", [])
                gaps = result.get("information_gaps", [])
                impression = result.get("initial_impression", "")

                # 合并已有症状（去重）
                existing_names = {s["name"] for s in state.get("symptoms", [])}
                merged = list(state.get("symptoms", []))
                for s in symptoms:
                    if s.get("name") and s["name"] not in existing_names:
                        merged.append(s)
                        existing_names.add(s["name"])

                # 合并信息缺口
                existing_gaps = set(state.get("information_gaps", []))
                merged_gaps = list(existing_gaps | set(gaps))

                print(f"  ✓ 提取到 {len(symptoms)} 个新症状 (总计 {len(merged)})")
                print(f"  ✓ 信息缺口: {', '.join(merged_gaps[:5])}")
                print(f"  ✓ 初步印象: {impression}")

                return {
                    "symptoms": merged,
                    "information_gaps": merged_gaps,
                }
        except Exception as e:
            print(f"  ✗ 症状提取失败: {e}")

        return {}

    # ══════════════════════════════════════════════════════════════
    #  工具 3: Search Books — 混合检索
    # ══════════════════════════════════════════════════════════════

    def _tool_search_books(self, state: AgentState) -> dict:
        """混合向量检索（Milvus Dense + ES Sparse）+ LLM Reranking"""
        action_input = state.get("action_input", {})
        search_query = action_input.get("query", state["query"])
        book_filter = action_input.get("books", state.get("books", []))
        top_k = action_input.get("top_k", 10)
        top_n = min(top_k, 5)

        print(f"\n📚 [Search Books] 检索: \"{search_query}\"")
        all_new_docs = []

        # 稠密向量检索
        if self.milvus_client:
            try:
                dense_results = self.milvus_client.Find_Information(search_query, top_k=top_k, book_filter=book_filter)
                dense_docs = self._process_dense_results(dense_results)
                all_new_docs.extend(dense_docs)
                print(f"  ✓ Dense (Milvus): {len(dense_docs)} 条")
            except Exception as e:
                print(f"  ✗ Dense 检索失败: {e}")

        # 稀疏向量检索
        if self.elasticsearch_client:
            try:
                sparse_results = self.elasticsearch_client.search_sparse(search_query, top_k=top_k, book_filter=book_filter)
                sparse_docs = self._process_sparse_results(sparse_results)
                all_new_docs.extend(sparse_docs)
                print(f"  ✓ Sparse (ES): {len(sparse_docs)} 条")
            except Exception as e:
                print(f"  ✗ Sparse 检索失败: {e}")

        # LLM Reranking
        if len(all_new_docs) > top_n:
            ranked_docs = self._rerank_documents(state["query"], all_new_docs, top_n)
        else:
            ranked_docs = all_new_docs

        # 去重合并
        existing_docs = list(state.get("retrieved_docs", []))
        existing_texts = {d["text"] for d in existing_docs}
        for doc in ranked_docs:
            if doc["text"] not in existing_texts:
                existing_docs.append(doc)
                existing_texts.add(doc["text"])

        print(f"  📊 本次 {len(ranked_docs)} 条，总计 {len(existing_docs)} 条")
        return {"retrieved_docs": existing_docs}

    # ══════════════════════════════════════════════════════════════
    #  工具 4: Ask Patient — 追问
    # ══════════════════════════════════════════════════════════════

    def _tool_ask_patient(self, state: AgentState) -> dict:
        """基于信息缺口生成专业追问"""
        action_input = state.get("action_input", {})
        question = action_input.get("question", "")

        if not question:
            # 根据信息缺口自动生成追问
            gaps = state.get("information_gaps", [])
            symptoms = state.get("symptoms", [])

            if gaps:
                gap_text = "、".join(gaps[:4])
                question = f"为了更准确地为您诊断，我还需要了解以下信息：{gap_text}。请您详细描述一下。"
            elif len(symptoms) < 2:
                question = "请您详细描述一下您的症状——包括什么部位不舒服、是什么样的感觉（胀痛、刺痛还是隐痛）、持续了多长时间、有没有伴随其他不适？"
            else:
                question = "请问您的舌头情况如何（颜色、舌苔厚薄）？脉搏感觉如何？最近的饮食和睡眠情况怎样？"

        reason = action_input.get("reason", "信息不足")

        print(f"\n❓ [Ask Patient] 追问: {question}")
        print(f"   原因: {reason}")

        return {
            "final_response": question,
            "action": "ask_patient",
        }

    # ══════════════════════════════════════════════════════════════
    #  工具 5: TCM Pattern Analysis — 辨证分析
    # ══════════════════════════════════════════════════════════════

    def _tool_tcm_pattern(self, state: AgentState) -> dict:
        """基于症状进行中医辨证分析"""
        print("\n☯ [TCM Pattern] 正在进行辨证分析...")
        try:
            symptoms_detail = json.dumps(state.get("symptoms", []), ensure_ascii=False, indent=2)
            retrieved_context = self._format_context(state.get("retrieved_docs", []))

            prompt = tcm_pattern_prompt_template.format(
                symptoms_detail=symptoms_detail,
                retrieved_context=retrieved_context
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                patterns = result.get("patterns", [])
                primary = result.get("primary_pattern", "")
                ba_gang = result.get("ba_gang", {})
                summary = result.get("analysis_summary", "")

                print(f"  ✓ 识别出 {len(patterns)} 个候选证候")
                print(f"  ✓ 主要证候: {primary}")
                print(f"  ✓ 八纲: {ba_gang}")
                print(f"  ✓ 分析: {summary[:100]}...")

                # 计算置信度
                max_conf = max([p.get("confidence", 0) for p in patterns]) if patterns else 0

                return {
                    "tcm_patterns": patterns,
                    "primary_pattern": primary,
                    "ba_gang": ba_gang,
                    "confidence_score": max_conf,
                }
        except Exception as e:
            print(f"  ✗ 辨证分析失败: {e}")

        return {}

    # ══════════════════════════════════════════════════════════════
    #  工具 6: Differential Diagnosis — 鉴别诊断
    # ══════════════════════════════════════════════════════════════

    def _tool_differential_dx(self, state: AgentState) -> dict:
        """多证候鉴别诊断"""
        print("\n🔍 [Differential Dx] 正在进行鉴别诊断...")
        try:
            patterns_detail = json.dumps(state.get("tcm_patterns", []), ensure_ascii=False, indent=2)
            symptoms_detail = json.dumps(state.get("symptoms", []), ensure_ascii=False, indent=2)
            retrieved_context = self._format_context(state.get("retrieved_docs", []))

            prompt = differential_diagnosis_prompt_template.format(
                patterns_detail=patterns_detail,
                symptoms_detail=symptoms_detail,
                retrieved_context=retrieved_context
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                ranked = result.get("ranked_diagnoses", [])
                overall_conf = result.get("overall_confidence", 0)
                confirmatory = result.get("recommended_confirmatory", [])

                print(f"  ✓ 鉴别结果: {len(ranked)} 个候选诊断")
                for i, d in enumerate(ranked[:3]):
                    print(f"    #{i+1} {d.get('diagnosis')} (P={d.get('probability', 0):.0%})")
                print(f"  ✓ 整体置信度: {overall_conf:.0%}")

                # 如果鉴别建议追问，扩展信息缺口
                existing_gaps = list(state.get("information_gaps", []))
                for item in confirmatory:
                    if item not in existing_gaps:
                        existing_gaps.append(item)

                return {
                    "diagnosis_hypotheses": ranked,
                    "confidence_score": overall_conf,
                    "information_gaps": existing_gaps,
                    "primary_pattern": ranked[0]["diagnosis"] if ranked else state.get("primary_pattern", ""),
                }
        except Exception as e:
            print(f"  ✗ 鉴别诊断失败: {e}")

        return {}

    # ══════════════════════════════════════════════════════════════
    #  工具 7: Check Safety — 安全检查
    # ══════════════════════════════════════════════════════════════

    def _tool_check_safety(self, state: AgentState) -> dict:
        """治疗方案安全性检查"""
        print("\n🛡️ [Check Safety] 正在进行安全检查...")
        try:
            diagnosis = state.get("primary_pattern", "未确定")
            symptoms_detail = json.dumps(state.get("symptoms", []), ensure_ascii=False)

            prompt = safety_check_prompt_template.format(
                diagnosis=diagnosis,
                treatment_principle=f"针对{diagnosis}的常规治法",
                symptoms_detail=symptoms_detail,
                patient_info="从对话历史中推断的病人信息"
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                flags = result.get("safety_flags", [])
                warnings = result.get("patient_warnings", [])
                risk = result.get("overall_risk", "low")
                is_safe = result.get("is_safe", True)

                print(f"  ✓ 安全: {'是' if is_safe else '否'} | 风险等级: {risk}")
                for flag in flags:
                    print(f"  ⚠️ [{flag.get('level')}] {flag.get('description')}")

                return {
                    "safety_flags": flags,
                }
        except Exception as e:
            print(f"  ✗ 安全检查失败: {e}")

        return {"safety_flags": []}

    # ══════════════════════════════════════════════════════════════
    #  Reflect — 自我反思
    # ══════════════════════════════════════════════════════════════

    def _reflect(self, state: AgentState) -> dict:
        """自我反思：检查当前诊疗过程的完备性和准确性"""
        print("\n🪞 [Reflect] 正在自我反思...")
        try:
            prompt = reflect_prompt_template.format(
                query=state["query"],
                symptom_count=len(state.get("symptoms", [])),
                gaps=", ".join(state.get("information_gaps", [])) or "无",
                pattern_count=len(state.get("tcm_patterns", [])),
                primary_pattern=state.get("primary_pattern", "未确定"),
                confidence=f"{state.get('confidence_score', 0):.0%}",
                doc_count=len(state.get("retrieved_docs", [])),
                executed_tools=", ".join(state.get("executed_tools", [])),
                iteration=state.get("current_iteration", 0),
                max_iterations=state.get("max_iterations", 6)
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                sufficiency = result.get("information_sufficiency", "insufficient")
                next_action = result.get("next_action", "ask_patient")
                critique = result.get("self_critique", "")
                red_flags = result.get("red_flags", [])

                print(f"  ✓ 信息充分度: {sufficiency}")
                print(f"  ✓ 建议下一步: {next_action}")
                print(f"  ✓ 自我批评: {critique[:100]}...")
                if red_flags:
                    for rf in red_flags:
                        print(f"  🚩 红旗: {rf}")

                return {
                    "action": next_action if next_action in self.VALID_ACTIONS else "ask_patient",
                    "thought": critique,
                }
        except Exception as e:
            print(f"  ✗ 反思失败: {e}")

        return {"action": "final_diagnosis"}

    # ══════════════════════════════════════════════════════════════
    #  Critique — 质量批评
    # ══════════════════════════════════════════════════════════════

    def _critique(self, state: AgentState) -> bool:
        """质量审核：检查诊疗方案是否通过质量关"""
        print("\n🧐 [Critique] 正在进行质量审核...")
        try:
            prompt = critique_prompt_template.format(
                diagnosis=state.get("primary_pattern", "未确定"),
                pattern_analysis=json.dumps(state.get("tcm_patterns", []), ensure_ascii=False)[:500],
                symptoms_used=json.dumps([s.get("name", "") for s in state.get("symptoms", [])], ensure_ascii=False),
                references=f"{len(state.get('retrieved_docs', []))} 条检索资料",
                safety_result=json.dumps(state.get("safety_flags", []), ensure_ascii=False)
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result:
                score = result.get("quality_score", 0)
                passed = result.get("passed", False)
                issues = result.get("issues", [])

                print(f"  ✓ 质量评分: {score}/10")
                print(f"  ✓ 通过: {'是' if passed else '否'}")
                for issue in issues:
                    print(f"  ⚠️ {issue}")

                return passed
        except Exception as e:
            print(f"  ✗ 质量批评失败: {e}")

        return True  # 失败时默认通过

    # ══════════════════════════════════════════════════════════════
    #  Plan — 诊疗计划生成
    # ══════════════════════════════════════════════════════════════

    def _generate_plan(self, state: AgentState) -> list:
        """生成诊疗计划"""
        print("\n📋 [Plan] 正在生成诊疗计划...")
        try:
            triage = state.get("triage_result", {})
            urgency = triage.get("urgency", "medium")
            urgency_map = {"low": "常规", "medium": "普通", "high": "紧急"}

            prompt = plan_prompt_template.format(
                urgency_text=urgency_map.get(urgency, "普通"),
                department=triage.get("department", "内科"),
                query=state["query"],
                symptoms_summary=self._summarize_symptoms(state.get("symptoms", [])),
                patterns_summary=self._summarize_patterns(state.get("tcm_patterns", [])),
                gaps_summary=", ".join(state.get("information_gaps", [])) or "暂无",
                doc_count=len(state.get("retrieved_docs", [])),
                confidence=f"{state.get('confidence_score', 0):.0%}"
            )
            result = self._parse_json_response(self._call_llm(prompt))
            if result and isinstance(result, list):
                # 验证步骤合法性
                valid_plan = [s for s in result if s in self.VALID_ACTIONS]
                print(f"  ✓ 生成计划: {' → '.join(valid_plan)}")
                return valid_plan
        except Exception as e:
            print(f"  ✗ 计划生成失败: {e}")

        # 默认计划
        symptoms = state.get("symptoms", [])
        if not symptoms:
            return ["extract_symptoms", "ask_patient"]
        return ["search_books", "tcm_pattern", "final_diagnosis"]

    # ══════════════════════════════════════════════════════════════
    #  ReAct 推理节点
    # ══════════════════════════════════════════════════════════════

    def _reason_node(self, state: AgentState) -> dict:
        """ReAct 推理：分析当前状态，决定下一步"""
        print(f"\n🧠 [Reason] 第 {state.get('current_iteration', 0) + 1} 轮推理...")
        try:
            prompt = react_system_template.format(
                symptoms_summary=self._summarize_symptoms(state.get("symptoms", [])),
                patterns_summary=self._summarize_patterns(state.get("tcm_patterns", [])),
                gaps_summary=", ".join(state.get("information_gaps", [])) or "暂无",
                confidence=f"{state.get('confidence_score', 0):.0%}",
                doc_count=len(state.get("retrieved_docs", [])),
                scratchpad=self._format_scratchpad(state.get("scratchpad", []))
            )
            human = react_human_template.format(
                query=state["query"],
                books=", ".join(state.get("books", [])) or "全部典籍",
                history=self._format_chat_history(state.get("chat_history", [])),
                iteration=state.get("current_iteration", 0) + 1,
                max_iterations=state.get("max_iterations", 6)
            )

            result_text = self._call_llm(prompt + "\n\n" + human)
            thought, action, action_input = self._parse_react_output(result_text, state.get("books", []))

            print(f"  Thought: {thought[:120]}...")
            print(f"  Action: {action}")
            print(f"  Input: {json.dumps(action_input, ensure_ascii=False)[:100]}")

            return {"thought": thought, "action": action, "action_input": action_input}
        except Exception as e:
            print(f"  ✗ 推理失败: {e}")
            return {"thought": str(e), "action": "final_diagnosis", "action_input": {}}

    # ══════════════════════════════════════════════════════════════
    #  主流式输出入口 — react_stream
    # ══════════════════════════════════════════════════════════════

    async def react_stream(self, info: dict) -> AsyncIterator[dict]:
        """
        高级 ReAct Agent 流式输出入口
        三阶段循环: Plan → Execute(tool by tool) → Reflect → Plan ...
        """
        query = info.get("content", info.get("query", ""))
        admin = info.get("admin", "AI助手")
        chat_history = info.get("chat_history", [])
        books = info.get("books", [])
        max_iterations = info.get("max_iterations", 6)

        # ── 初始化认知状态 ──
        state: AgentState = {
            "query": query, "admin": admin, "chat_history": chat_history, "books": books,
            "triage_result": {}, "symptoms": [], "tcm_patterns": [], "diagnosis_hypotheses": [],
            "information_gaps": [], "safety_flags": [], "primary_pattern": "", "ba_gang": {},
            "diagnostic_plan": [], "plan_step_index": 0, "scratchpad": [],
            "retrieved_docs": [], "current_iteration": 0, "max_iterations": max_iterations,
            "executed_tools": [], "thought": "", "action": "", "action_input": {},
            "confidence_score": 0.0, "final_response": "",
        }

        thinking_steps = []
        start_time = time.time()

        try:
            # ════════════════════════════════════════
            # Phase 0: Triage — 意图分类
            # ════════════════════════════════════════
            step_triage = {"icon": "🔖", "title": "导诊分类", "details": "正在分析您的问诊意图和紧急程度..."}
            thinking_steps.append(step_triage)
            yield {"thinking_step": step_triage}

            triage_result = await asyncio.get_event_loop().run_in_executor(None, self._tool_triage, state)
            state.update(triage_result)
            state["executed_tools"].append("triage")

            triage = state["triage_result"]
            step_triage["details"] = f"意图: {triage.get('intent', '问诊')} | 科室: {triage.get('department', '内科')} | 紧急: {triage.get('urgency', 'medium')}"
            yield {"thinking_update": step_triage}

            # ════════════════════════════════════════
            # 主循环: Plan → Execute → Reflect
            # ════════════════════════════════════════
            iteration = 0
            while iteration < max_iterations:
                iteration += 1
                state["current_iteration"] = iteration
                elapsed = time.time() - start_time
                print(f"\n{'#'*60}")
                print(f"# 迭代 {iteration}/{max_iterations} (已用 {elapsed:.1f}s)")
                print(f"{'#'*60}")

                # ──── Phase 1: Plan ────
                step_plan = {"icon": "📋", "title": f"制定诊疗计划（第{iteration}轮）", "details": "正在规划下一步诊疗路径..."}
                thinking_steps.append(step_plan)
                yield {"thinking_step": step_plan}

                plan = await asyncio.get_event_loop().run_in_executor(None, self._generate_plan, state)
                state["diagnostic_plan"] = plan
                state["plan_step_index"] = 0

                step_plan["details"] = f"计划: {' → '.join(plan)}"
                yield {"thinking_update": step_plan}

                # ──── Phase 2: Execute (按计划逐步执行) ────
                for step_idx, tool_name in enumerate(plan):
                    state["plan_step_index"] = step_idx

                    # 特殊处理: ask_patient 中断循环
                    if tool_name == "ask_patient":
                        step_ask = {"icon": "❓", "title": "望闻问切 · 追问病人", "details": "正在基于信息缺口生成专业追问..."}
                        thinking_steps.append(step_ask)
                        yield {"thinking_step": step_ask}

                        # 先用 ReAct 推理生成追问
                        state["action"] = "ask_patient"
                        reason_result = await asyncio.get_event_loop().run_in_executor(None, self._reason_node, state)
                        state.update(reason_result)

                        ask_result = await asyncio.get_event_loop().run_in_executor(None, self._tool_ask_patient, state)
                        state.update(ask_result)
                        state["executed_tools"].append("ask_patient")

                        question = state["final_response"]
                        step_ask["details"] = question
                        yield {"thinking_update": step_ask}

                        yield {"thinking_complete": True, "thinking_steps": thinking_steps}
                        yield {"partial_result": question}
                        yield {"result": question}
                        return

                    # 特殊处理: final_diagnosis 结束循环
                    if tool_name == "final_diagnosis":
                        # 先执行安全检查（如果还没做过）
                        if "check_safety" not in state["executed_tools"]:
                            step_safety = {"icon": "🛡️", "title": "安全性检查", "details": "正在检查治疗方案的安全性..."}
                            thinking_steps.append(step_safety)
                            yield {"thinking_step": step_safety}

                            safety_result = await asyncio.get_event_loop().run_in_executor(None, self._tool_check_safety, state)
                            state.update(safety_result)
                            state["executed_tools"].append("check_safety")

                            flags = state.get("safety_flags", [])
                            step_safety["details"] = f"发现 {len(flags)} 个安全提醒" if flags else "安全检查通过 ✓"
                            yield {"thinking_update": step_safety}

                        # 质量批评
                        step_critique = {"icon": "🧐", "title": "质量审核", "details": "正在进行诊疗方案质量审核..."}
                        thinking_steps.append(step_critique)
                        yield {"thinking_step": step_critique}

                        passed = await asyncio.get_event_loop().run_in_executor(None, self._critique, state)
                        step_critique["details"] = "质量审核通过 ✓" if passed else "发现需要改进的问题"
                        yield {"thinking_update": step_critique}

                        if not passed and iteration < max_iterations:
                            # 质量不过关，回到 Plan 重新规划
                            print("  ⚠️ 质量审核未通过，重新规划")
                            continue
                        break  # 跳出 plan 循环，进入最终生成

                    # ── 普通工具执行 ──
                    tool_configs = {
                        "extract_symptoms": ("🔬", "症状结构化提取", self._tool_extract_symptoms),
                        "search_books":     ("📚", "检索中医典籍", self._tool_search_books),
                        "tcm_pattern":      ("☯",  "辨证论治分析", self._tool_tcm_pattern),
                        "differential_dx":  ("🔍", "鉴别诊断排序", self._tool_differential_dx),
                        "check_safety":     ("🛡️", "安全性检查",   self._tool_check_safety),
                    }

                    if tool_name in tool_configs:
                        icon, title, tool_fn = tool_configs[tool_name]
                        step_tool = {"icon": icon, "title": title, "details": f"正在执行 {tool_name}..."}
                        thinking_steps.append(step_tool)
                        yield {"thinking_step": step_tool}

                        # 如果是 search_books，先用 ReAct 推理确定检索关键词
                        if tool_name == "search_books":
                            reason_result = await asyncio.get_event_loop().run_in_executor(None, self._reason_node, state)
                            state.update(reason_result)

                        tool_result = await asyncio.get_event_loop().run_in_executor(None, tool_fn, state)
                        state.update(tool_result)
                        state["executed_tools"].append(tool_name)

                        # 更新步骤详情
                        detail = self._get_tool_detail(tool_name, state)
                        step_tool["details"] = detail
                        yield {"thinking_update": step_tool}

                        # 记录 scratchpad
                        state["scratchpad"].append({
                            "iteration": iteration,
                            "tool": tool_name,
                            "thought": state.get("thought", ""),
                            "observation": detail,
                        })

                else:
                    # Plan 中的所有步骤都执行完毕（没有 break）
                    # ──── Phase 3: Reflect ────
                    step_reflect = {"icon": "🪞", "title": "自我反思", "details": "正在审视诊疗过程的完备性..."}
                    thinking_steps.append(step_reflect)
                    yield {"thinking_step": step_reflect}

                    reflect_result = await asyncio.get_event_loop().run_in_executor(None, self._reflect, state)
                    next_action = reflect_result.get("action", "final_diagnosis")
                    critique_text = reflect_result.get("thought", "")

                    step_reflect["details"] = f"反思: {critique_text[:100]}... → 建议: {next_action}"
                    yield {"thinking_update": step_reflect}

                    # 根据反思结果决定：继续循环 or 结束
                    if next_action == "final_diagnosis" and state.get("confidence_score", 0) >= 0.6:
                        break
                    if next_action == "ask_patient":
                        state["diagnostic_plan"] = ["ask_patient"]
                        continue  # 回到 Plan，但 plan 里只有 ask_patient

                    # 其他情况继续循环到下一轮 Plan
                    continue

                # 如果从 final_diagnosis 的 break 出来，也退出主循环
                break

            # ════════════════════════════════════════
            # Phase Final: 流式生成最终诊疗建议
            # ════════════════════════════════════════

            step_final = {
                "icon": "✅",
                "title": "生成诊疗建议",
                "details": f"基于 {len(state.get('symptoms', []))} 个症状 · {len(state.get('retrieved_docs', []))} 条资料 · 证候: {state.get('primary_pattern', '综合分析')}"
            }
            thinking_steps.append(step_final)
            yield {"thinking_step": step_final}
            yield {"thinking_complete": True, "thinking_steps": thinking_steps}

            # 构建 RAG 最终回答
            context = self._format_context(state.get("retrieved_docs", []))
            if not context or context == "暂无检索资料。":
                context = "暂无检索资料，请基于您的临床经验回答。"

            # 增强上下文：附加辨证和安全信息
            enhanced_context = context
            if state.get("primary_pattern"):
                enhanced_context += f"\n\n【辨证结论】主要证候: {state['primary_pattern']}"
            if state.get("ba_gang"):
                bg = state["ba_gang"]
                enhanced_context += f"\n八纲: 阴阳={bg.get('yin_yang','?')} 表里={bg.get('biao_li','?')} 寒热={bg.get('han_re','?')} 虚实={bg.get('xu_shi','?')}"
            if state.get("safety_flags"):
                sf = state["safety_flags"]
                enhanced_context += f"\n\n【安全提醒】共 {len(sf)} 条安全提醒：" + "; ".join([f.get("description", "") for f in sf])

            history_messages = self._convert_chat_history(chat_history)
            inputs = {
                "admin": admin, "query": query,
                "context": enhanced_context, "history": history_messages,
            }

            full_text = ""
            print(f"\n🤖 进入流式生成 (用时 {time.time() - start_time:.1f}s)")

            try:
                async for chunk in self.rag_chain.astream(inputs):
                    content = getattr(chunk, "content", str(chunk))
                    full_text += content
                    yield {"partial_result": content}
                yield {"result": full_text}
            except Exception as e:
                print(f"  ✗ 流式生成失败: {e}")
                yield {"error": str(e), "partial_result": f"抱歉，生成回答时遇到技术问题: {e}"}

        except Exception as e:
            print(f"❌ ReAct Agent 异常: {e}")
            yield {"error": str(e), "partial_result": "抱歉，在处理您的请求时遇到了技术问题。"}

    # ══════════════════════════════════════════════════════════════
    #  辅助工具方法
    # ══════════════════════════════════════════════════════════════

    def _parse_react_output(self, text: str, default_books: list) -> tuple:
        """解析 ReAct 格式输出 → (thought, action, action_input)"""
        thought, action, action_input = "", "final_diagnosis", {}
        try:
            thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:)', text, re.DOTALL)
            if thought_match:
                thought = thought_match.group(1).strip()

            action_match = re.search(r'Action:\s*(\S+)', text)
            if action_match:
                raw = action_match.group(1).strip().lower()
                if raw in self.VALID_ACTIONS:
                    action = raw

            input_match = re.search(r'Action Input:\s*(\{.*?\})', text, re.DOTALL)
            if not input_match:
                input_match = re.search(r'Action Input:\s*(\{.*\})', text, re.DOTALL)
            if input_match:
                try:
                    action_input = json.loads(input_match.group(1))
                except json.JSONDecodeError:
                    pass

            if action == "search_books":
                action_input.setdefault("books", default_books)
                action_input.setdefault("query", thought[:50] if thought else "")
            if action == "ask_patient" and "question" not in action_input:
                action_input["question"] = thought or "请详细描述症状"
        except Exception as e:
            print(f"  ⚠️ 解析失败: {e}")
            thought = text[:200]

        return thought, action, action_input

    def _rerank_documents(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """LLM Reranking"""
        try:
            if len(docs) <= top_n:
                return docs
            from BaseOne.Prompts.MyPrompt import doc_processor_prompt
            doc_texts = []
            for i, doc in enumerate(docs):
                t = f"文档[{i+1}]: "
                if doc.get("is_image"): t += "[图像] "
                t += doc["text"][:200]
                t += f" [来源: {doc.get('source', '?')}]"
                doc_texts.append(t)
            inputs = {"query": query, "docs": "\n\n".join(doc_texts), "top_n": top_n}
            response = ChatBase.invoke(doc_processor_prompt.format_messages(**inputs))
            match = re.search(r'\[.*?\]', response.content)
            if match:
                indices = json.loads(match.group())
                valid = [i for i in indices if 1 <= i <= len(docs)]
                if valid:
                    return [docs[i-1] for i in valid]
        except Exception as e:
            print(f"  ⚠️ Reranking 失败: {e}")
        docs.sort(key=lambda x: x.get("score", 0), reverse=True)
        return docs[:top_n]

    @staticmethod
    def _process_dense_results(results: list) -> List[Dict]:
        docs = []
        for hit_list in results:
            for hit in hit_list:
                docs.append({"text": hit.get("text", ""), "page_number": hit.get("page_number", 0),
                             "is_image": hit.get("is_image_description", False),
                             "score": hit.get("distance", 0), "source": "dense"})
        return docs

    @staticmethod
    def _process_sparse_results(results: list) -> List[Dict]:
        return [{"text": h.get("text", ""), "page_number": h.get("page_number", 0),
                 "is_image": h.get("is_image_description", False),
                 "score": h.get("score", 0), "source": "sparse"} for h in results]

    @staticmethod
    def _format_context(docs: List[Dict]) -> str:
        if not docs: return "暂无检索资料。"
        parts = []
        for i, d in enumerate(docs):
            t = f"[文档{i+1}] "
            if d.get("is_image"): t += "[图像描述] "
            t += d["text"]
            if d.get("page_number"): t += f" (页码: {d['page_number']})"
            t += f" [来源: {d.get('source', '?')}]"
            parts.append(t)
        return "\n\n".join(parts)

    @staticmethod
    def _format_chat_history(chat_history) -> str:
        if not chat_history: return "暂无聊天记录。"
        lines = []
        if hasattr(chat_history, 'messages'):
            for msg in chat_history.messages:
                role = "病人" if msg.type == "human" else "老中医"
                lines.append(f"{role}: {msg.content}")
        elif isinstance(chat_history, list):
            for msg in chat_history:
                if isinstance(msg, dict):
                    role = "病人" if msg.get("role") == "user" else "老中医"
                    lines.append(f"{role}: {msg.get('content', '')}")
                elif hasattr(msg, 'type'):
                    role = "病人" if msg.type == "human" else "老中医"
                    lines.append(f"{role}: {msg.content}")
        return "\n".join(lines) if lines else "暂无聊天记录。"

    @staticmethod
    def _convert_chat_history(chat_history) -> list:
        messages = []
        if hasattr(chat_history, 'messages'):
            return chat_history.messages
        elif isinstance(chat_history, list):
            for msg in chat_history:
                if isinstance(msg, dict) and "role" in msg and "content" in msg:
                    if msg["role"] == "user": messages.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant": messages.append(AIMessage(content=msg["content"]))
                elif hasattr(msg, 'type'):
                    messages.append(msg)
        return messages

    @staticmethod
    def _summarize_symptoms(symptoms: list) -> str:
        if not symptoms: return "暂无"
        return ", ".join([f"{s.get('name', '?')}({s.get('confidence', 0):.0%})" for s in symptoms[:8]])

    @staticmethod
    def _summarize_patterns(patterns: list) -> str:
        if not patterns: return "暂无"
        return ", ".join([f"{p.get('pattern_name', '?')}({p.get('confidence', 0):.0%})" for p in patterns[:5]])

    @staticmethod
    def _format_scratchpad(scratchpad: list) -> str:
        if not scratchpad: return "暂无推理记录。"
        lines = []
        for entry in scratchpad:
            lines.append(f"--- 迭代 {entry.get('iteration', '?')} [{entry.get('tool', '?')}] ---")
            if entry.get("thought"): lines.append(f"  Thought: {entry['thought'][:150]}")
            if entry.get("observation"): lines.append(f"  Observation: {entry['observation'][:150]}")
        return "\n".join(lines)

    @staticmethod
    def _get_tool_detail(tool_name: str, state: AgentState) -> str:
        """获取工具执行后的可读摘要"""
        if tool_name == "extract_symptoms":
            symptoms = state.get("symptoms", [])
            gaps = state.get("information_gaps", [])
            return f"提取到 {len(symptoms)} 个症状 | 信息缺口: {', '.join(gaps[:4]) or '无'}"
        elif tool_name == "search_books":
            return f"检索到 {len(state.get('retrieved_docs', []))} 条相关文档"
        elif tool_name == "tcm_pattern":
            p = state.get("primary_pattern", "未确定")
            c = state.get("confidence_score", 0)
            return f"主要证候: {p} (置信度: {c:.0%})"
        elif tool_name == "differential_dx":
            hyps = state.get("diagnosis_hypotheses", [])
            if hyps:
                top = hyps[0]
                return f"首选: {top.get('diagnosis', '?')} ({top.get('probability', 0):.0%})"
            return "鉴别完成"
        elif tool_name == "check_safety":
            flags = state.get("safety_flags", [])
            return f"{len(flags)} 个安全提醒" if flags else "安全检查通过 ✓"
        return "完成"
