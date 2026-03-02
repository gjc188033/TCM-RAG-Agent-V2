"""
RagAgent — 船代智能问答助手 RAG 编排器

职责：
  - 封装 ReActAgent，通过 react_stream 对外提供流式服务
  - 保留旧版 document_assistant_stream / rag_stream 作为 fallback
  - 管理 ES 检索客户端和术语库客户端的生命周期
"""

from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from core.foundation.llm_client import ChatBase
from core.templates.prompt_registry import (
    system_prompt,
    human_prompt,
    rag_system_prompt,
    rag_human_prompt,
    doc_processor_prompt
)
import asyncio
import json
from typing import AsyncIterator, Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage, AIMessage
from .es_client import ElasticsearchDB
from .reasoning_engine import ReActAgent


class RagAgent:
    def __init__(self, redis_url, session_id, elasticsearch_client=None, terminology_client=None):

        self.redis_url = redis_url
        self.session_id = session_id

        self.rag_prompt = ChatPromptTemplate.from_messages([rag_system_prompt, MessagesPlaceholder("history"), rag_human_prompt])

        # 使用RAG提示词的链
        self.rag_chain = self.rag_prompt | ChatBase

        # 初始化聊天记录
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

        # 初始化Elasticsearch客户端
        try:
            self.elasticsearch_client = elasticsearch_client or ElasticsearchDB()
            print("✅ Elasticsearch客户端初始化成功")
        except Exception as e:
            print(f"❌ Elasticsearch客户端初始化失败: {e}")
            self.elasticsearch_client = None

        # 术语库客户端
        self.terminology_client = terminology_client

        # 初始化 ReAct Agent
        self.react_agent = ReActAgent(
            redis_url=redis_url,
            session_id=session_id,
            elasticsearch_client=self.elasticsearch_client,
            terminology_client=self.terminology_client,
        )

        # 创建图结构（保留旧版 fallback）
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("RagNode", self.rag_stream)
        graph.set_entry_point("RagNode")
        graph.set_finish_point("RagNode")
        return graph.compile()

    def process_sparse_results(self, retrieval_results_sparse: List) -> List[Dict]:
        """格式化稀疏向量检索结果"""
        docs = []
        for hit in retrieval_results_sparse:
            text = hit.get("text", "")
            page_number = hit.get("page_number", 0)
            is_image = hit.get("is_image_description", False)

            docs.append({
                "text": text,
                "page_number": page_number,
                "is_image": is_image,
                "score": hit.get("score", 0),
                "source": "elasticsearch"
            })
        return docs

    def format_context(self, docs: List[Dict]) -> str:
        """将检索到的文档格式化为上下文字符串"""
        formatted_context = ""
        for i, doc in enumerate(docs):
            text = doc["text"]
            page_number = doc["page_number"]
            is_image = doc["is_image"]
            source = doc.get("source", "未知")

            doc_text = f"[文档{i + 1}] "
            if is_image:
                doc_text += "[图表描述] "
            doc_text += text
            if page_number:
                doc_text += f" (位置: {page_number})"
            doc_text += f" [来源: {source}]"

            formatted_context += doc_text + "\n\n"

        return formatted_context.strip()

    def generate_related_questions(self, query: str, num_questions: int = 5) -> List[str]:
        """根据原始问题生成相关问题用于扩展检索"""
        try:
            print("\n" + "=" * 50)
            print("🧠 生成相关问题...")
            print("=" * 50)

            prompt = f"""你是一位精通航运船代业务的助手。请根据用户的原始问题，生成{num_questions}个相关的问题，这些问题应该从不同角度探索原始问题的相关内容。
这些问题将用于检索相关的规章制度和操作规范，所以应该具有明确的关键词和具体的内容焦点。

原始问题: {query}

请生成{num_questions}个相关问题，每个问题一行，不要有编号或其他格式。只返回问题列表，不要有任何解释或其他文字。"""

            response = ChatBase.invoke([HumanMessage(content=prompt)])
            result_text = response.content

            questions = [q.strip() for q in result_text.strip().split('\n') if q.strip()]

            while len(questions) < num_questions:
                questions.append(query)

            questions = questions[:num_questions]

            print(f"✅ 生成了{len(questions)}个相关问题:")
            for i, q in enumerate(questions):
                print(f"  {i + 1}. {q}")

            return questions

        except Exception as e:
            print(f"❌ 生成相关问题失败: {str(e)}")
            return [query] * num_questions

    def retrieve_documents(self, queries: List[str], top_k: int = 5, book_filter: List[str] = None) -> List[Dict]:
        """使用多个查询从Elasticsearch中检索文档"""
        all_docs = []

        try:
            print("\n" + "=" * 50)
            print("🔍 从知识库检索文档...")
            print("=" * 50)
            
            if book_filter and len(book_filter) > 0:
                print(f"📚 应用知识库来源过滤: {', '.join(book_filter)}")

            for i, query in enumerate(queries):
                print(f"\n查询 {i + 1}: {query}")

                # Elasticsearch 检索
                if self.elasticsearch_client:
                    try:
                        sparse_results = self.elasticsearch_client.search_sparse(
                            query, 
                            top_k=top_k,
                            book_filter=book_filter
                        )
                        sparse_docs = self.process_sparse_results(sparse_results)
                        all_docs.extend(sparse_docs)
                        print(f"  ✓ ES检索: 找到 {len(sparse_docs)} 条结果")
                    except Exception as e:
                        print(f"  ✗ ES检索失败: {str(e)}")

            print(f"\n✅ 共检索到 {len(all_docs)} 条结果")

            return all_docs

        except Exception as e:
            print(f"❌ 文档检索失败: {str(e)}")
            return []

    def rank_documents(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """使用LLM对文档进行相关性排序"""
        try:
            if len(docs) <= top_n:
                return docs

            print("\n" + "=" * 50)
            print("🧠 使用LLM对文档进行相关性排序...")
            print("=" * 50)

            doc_texts = []
            for i, doc in enumerate(docs):
                doc_text = f"文档[{i + 1}]: "
                if doc["is_image"]:
                    doc_text += "[图表描述] "
                doc_text += doc["text"]
                if doc["page_number"]:
                    doc_text += f" (位置: {doc['page_number']})"
                doc_text += f" [来源: {doc['source']}]"
                doc_texts.append(doc_text)

            all_docs_text = "\n\n".join(doc_texts)

            inputs = {
                "query": query,
                "docs": all_docs_text,
                "top_n": top_n
            }

            response = ChatBase.invoke(doc_processor_prompt.format_messages(**inputs))
            result_text = response.content

            print(f"LLM排序结果: {result_text}")

            import re

            json_match = re.search(r'\[.*?\]', result_text)
            if json_match:
                try:
                    selected_indices = json.loads(json_match.group())
                    valid_indices = [idx for idx in selected_indices if 1 <= idx <= len(docs)]

                    if not valid_indices:
                        print("⚠️ LLM未返回有效索引，使用得分排序")
                        docs.sort(key=lambda x: x["score"], reverse=True)
                        return docs[:top_n]

                    selected_docs = [docs[idx - 1] for idx in valid_indices if idx <= len(docs)]

                    print(f"✅ 成功筛选出{len(selected_docs)}个相关文档")
                    return selected_docs

                except json.JSONDecodeError:
                    print("⚠️ 无法解析LLM返回的JSON，使用得分排序")
            else:
                print("⚠️ LLM返回格式不符合预期，使用得分排序")

            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

        except Exception as e:
            print(f"❌ 文档排序失败: {str(e)}")
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

    async def document_assistant_stream(self, query: str, top_k: int = 5, top_n: int = 5, book_filter: List[str] = None):
        """流式文档助手：生成相关问题，检索文档，排序文档"""
        thinking_steps = []

        try:
            # 1. 生成相关问题
            step1 = {
                "icon": "🔍",
                "title": "生成相关问题",
                "details": "基于您的问题，生成相关的扩展问题以提高检索准确性"
            }
            thinking_steps.append(step1)
            yield {"status": "thinking_step", "step": step1}

            related_questions = self.generate_related_questions(query)

            step1["details"] = f"生成了{len(related_questions)}个相关问题：\n" + "\n".join([f"• {q}" for q in related_questions[:3]])
            if len(related_questions) > 3:
                step1["details"] += f"\n• 等共{len(related_questions)}个问题"
            yield {"status": "thinking_update", "step": step1}

            all_queries = [query] + related_questions

            # 2. 使用所有查询检索文档
            step2 = {
                "icon": "📚",
                "title": "检索知识库",
                "details": f"从{'、'.join(book_filter) if book_filter else '全部知识库'}中检索相关资料"
            }
            thinking_steps.append(step2)
            yield {"status": "thinking_step", "step": step2}

            all_docs = self.retrieve_documents(all_queries, top_k, book_filter)

            sparse_count = len(all_docs)
            step2["details"] = f"检索到{sparse_count}条文档"
            yield {"status": "thinking_update", "step": step2}

            # 3. 对文档进行排序
            step3 = {
                "icon": "🧠",
                "title": "AI智能排序",
                "details": f"使用AI对{len(all_docs)}条文档进行相关性分析和排序"
            }
            thinking_steps.append(step3)
            yield {"status": "thinking_step", "step": step3}

            ranked_docs = await self.rank_documents_async(query, all_docs, top_n)

            step3["details"] = f"筛选出{len(ranked_docs)}条最相关的文档用于回答"
            yield {"status": "thinking_update", "step": step3}

            yield {"status": "complete", "documents": ranked_docs, "thinking_steps": thinking_steps}

        except Exception as e:
            print(f"❌ 文档助手处理失败: {str(e)}")
            yield {"status": "error", "error": str(e), "thinking_steps": thinking_steps}

    async def rank_documents_async(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """异步版本的文档排序方法"""
        try:
            if len(docs) <= top_n:
                return docs

            doc_texts = []
            for i, doc in enumerate(docs):
                doc_text = f"文档[{i + 1}]: "
                if doc["is_image"]:
                    doc_text += "[图表描述] "
                doc_text += doc["text"]
                if doc["page_number"]:
                    doc_text += f" (位置: {doc['page_number']})"
                doc_text += f" [来源: {doc['source']}]"
                doc_texts.append(doc_text)

            all_docs_text = "\n\n".join(doc_texts)

            inputs = {
                "query": query,
                "docs": all_docs_text,
                "top_n": top_n
            }

            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ChatBase.invoke(doc_processor_prompt.format_messages(**inputs))
            )
            result_text = response.content

            import re

            json_match = re.search(r'\[.*?\]', result_text)
            if json_match:
                try:
                    selected_indices = json.loads(json_match.group())
                    valid_indices = [idx for idx in selected_indices if 1 <= idx <= len(docs)]

                    if not valid_indices:
                        docs.sort(key=lambda x: x["score"], reverse=True)
                        return docs[:top_n]

                    selected_docs = [docs[idx - 1] for idx in valid_indices if idx <= len(docs)]
                    return selected_docs

                except json.JSONDecodeError:
                    pass

            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

        except Exception as e:
            print(f"❌ 文档排序失败: {str(e)}")
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

    async def rag_stream(self, state: dict):
        """旧版流式RAG节点（fallback）"""
        try:
            query = state.get("content", state.get("query", ""))
            admin = state["admin"]
            chat_history = state["chat_history"]
            top_k = state.get("top_k", 5)
            top_n = min(top_k, 5)
            book_filter = state.get("books", [])

            filtered_docs = None
            thinking_steps = []

            async for doc_update in self.document_assistant_stream(query, top_k, top_n, book_filter):
                if doc_update["status"] == "thinking_step":
                    step = doc_update["step"]
                    thinking_steps.append(step)
                    yield {"thinking_step": step}
                elif doc_update["status"] == "thinking_update":
                    yield {"thinking_update": doc_update["step"]}
                elif doc_update["status"] == "complete":
                    filtered_docs = doc_update["documents"]
                    if "thinking_steps" in doc_update:
                        thinking_steps = doc_update["thinking_steps"]
                    break
                elif doc_update["status"] == "error":
                    yield {"partial_result": f"❌ 文档处理出错: {doc_update['error']}"}
                    return

            if not filtered_docs:
                yield {"partial_result": "❌ 未能获取到相关文档"}
                return

            formatted_context = self.format_context(filtered_docs)

            inputs = {
                "admin": admin,
                "query": query,
                "context": formatted_context
            }

            if hasattr(chat_history, 'messages'):
                inputs["history"] = chat_history.messages
            elif isinstance(chat_history, list):
                messages = []
                try:
                    for msg in chat_history:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            if msg["role"] == "user":
                                messages.append(HumanMessage(content=msg["content"]))
                            elif msg["role"] == "assistant":
                                messages.append(AIMessage(content=msg["content"]))
                    inputs["history"] = messages
                except Exception as e:
                    inputs["history"] = []
            else:
                inputs["history"] = []

            yield {"thinking_complete": True, "thinking_steps": thinking_steps}

            full_text = ""
            try:
                async for chunk in self.rag_chain.astream(inputs):
                    content = getattr(chunk, "content", str(chunk))
                    full_text += content
                    yield {"partial_result": content}

                yield {"result": full_text}
            except Exception as e:
                yield {
                    "error": f"生成回答时发生错误: {str(e)}",
                    "partial_result": f"抱歉，在处理您的问题时遇到了技术问题: {str(e)}"
                }

        except Exception as e:
            yield {
                "error": f"处理请求时发生错误: {str(e)}",
                "partial_result": "抱歉，在处理您的请求时遇到了技术问题。"
            }

    # ──────────────────────────────────────────
    #  ReAct Agent 流式输出（主入口）
    # ──────────────────────────────────────────

    async def react_stream(self, state: dict):
        """
        使用 ReAct Agent 进行流式推理和回答
        替代原有的 rag_stream 固定流水线
        """
        async for chunk in self.react_agent.react_stream(state):
            yield chunk
