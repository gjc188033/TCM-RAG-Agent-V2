from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from BaseOne.utils.llms import ChatBase
from BaseOne.Prompts.MyPrompt import (
    system_prompt,
    human_prompt,
    rag_system_prompt,
    rag_human_prompt,
    doc_processor_prompt
)
from .MilvusWoker import MilvusDB
from .config import MILVUS_URI, MILVUS_USER, MILVUS_PASSWORD, MILVUS_COLLECTION
import asyncio
import json
from typing import AsyncIterator, Dict, Any, List, Tuple
from langchain_core.messages import HumanMessage, AIMessage
from .ElasticsearchWoker import ElasticsearchDB
from .ReActAgent import ReActAgent


class RagAgent:
    def __init__(self, redis_url, session_id, milvus_client=None):

        self.redis_url = redis_url
        self.session_id = session_id

        self.rag_prompt = ChatPromptTemplate.from_messages([rag_system_prompt, MessagesPlaceholder("history"), rag_human_prompt])

        # 使用RAG提示词的链
        self.rag_chain = self.rag_prompt | ChatBase

        # 初始化聊天记录
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

        try:
            # 初始化Elasticsearch客户端
            self.elasticsearch_client = ElasticsearchDB()
            print("✅ Elasticsearch客户端初始化成功")
        except Exception as e:
            print(f"❌ Elasticsearch客户端初始化失败: {e}")
            self.elasticsearch_client = None

        # 初始化向量数据库客户端
        try:
            if milvus_client:
                # 使用预加载的向量数据库客户端
                self.milvus_client = milvus_client
            else:
                # 创建新的向量数据库客户端
                self.milvus_client = MilvusDB(uri=MILVUS_URI, user=MILVUS_USER, password=MILVUS_PASSWORD,collection=MILVUS_COLLECTION)
            print("✅ Milvus客户端初始化成功")
        except Exception as e:
            print(f"❌ Milvus客户端初始化失败: {e}")
            self.milvus_client = None

        # 初始化 ReAct Agent
        self.react_agent = ReActAgent(
            redis_url=redis_url,
            session_id=session_id,
            milvus_client=self.milvus_client,
        )

        # 创建图结构（保留旧版 fallback）
        self.graph = self._build_graph()

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("RagNode", self.rag_stream)
        graph.set_entry_point("RagNode")
        graph.set_finish_point("RagNode")
        return graph.compile()

    def process_dense_results(self, retrieval_results_dense: List) -> List[Dict]:
        # is 格式化稠密向量检索结果
        docs = []
        for hit_list in retrieval_results_dense:
            for i, hit in enumerate(hit_list):
                text = hit.get("text", "")
                page_number = hit.get("page_number", 0)
                is_image = hit.get("is_image_description", False)

                docs.append({
                    "text": text,
                    "page_number": page_number,
                    "is_image": is_image,
                    "score": hit.get("distance", 0),
                    "source": "dense"
                })
        return docs

    def process_sparse_results(self, retrieval_results_sparse: List) -> List[Dict]:
        # is 格式化稀疏向量检索结果
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
                "source": "sparse"
            })
        return docs

    def format_context(self, docs: List[Dict]) -> str:
        """is 将检索到的文档格式化为上下文字符串，添加文档编号、页码和来源信息，返回：格式化的文本字符串"""
        formatted_context = ""
        for i, doc in enumerate(docs):
            text = doc["text"]
            page_number = doc["page_number"]
            is_image = doc["is_image"]
            source = doc.get("source", "未知")

            doc_text = f"[文档{i + 1}] "
            if is_image:
                doc_text += "[图像描述] "
            doc_text += text
            if page_number:
                doc_text += f" (页码: {page_number})"
            doc_text += f" [来源: {source}]"

            formatted_context += doc_text + "\n\n"

        return formatted_context.strip()

    def generate_related_questions(self, query: str, num_questions: int = 5) -> List[str]:
        """
        根据原始问题生成相关问题

        参数:
            query: 原始问题
            num_questions: 要生成的问题数量

        返回:
            相关问题列表
        """
        try:
            print("\n" + "=" * 50)
            print("🧠 生成相关问题...")
            print("=" * 50)

            # 构建提示词
            prompt = f"""你是一位精通中医知识的助手。请根据用户的原始问题，生成{num_questions}个相关的问题，这些问题应该从不同角度探索原始问题的相关内容。
这些问题将用于检索相关文档，所以应该具有明确的关键词和具体的内容焦点。

原始问题: {query}

请生成{num_questions}个相关问题，每个问题一行，不要有编号或其他格式。只返回问题列表，不要有任何解释或其他文字。"""

            # 调用LLM模型生成相关问题
            response = ChatBase.invoke([HumanMessage(content=prompt)])
            result_text = response.content

            # 处理结果，按行分割
            questions = [q.strip() for q in result_text.strip().split('\n') if q.strip()]

            # 如果生成的问题不足，使用原始问题补充
            while len(questions) < num_questions:
                questions.append(query)

            # 如果生成的问题过多，只保留指定数量
            questions = questions[:num_questions]

            print(f"✅ 生成了{len(questions)}个相关问题:")
            for i, q in enumerate(questions):
                print(f"  {i + 1}. {q}")

            return questions

        except Exception as e:
            print(f"❌ 生成相关问题失败: {str(e)}")
            # 如果生成失败，返回原始问题
            return [query] * num_questions

    def retrieve_documents(self, queries: List[str], top_k: int = 5, book_filter: List[str] = None) -> List[Dict]:
        """
        使用多个查询从两个向量数据库中检索文档

        参数:
            queries: 查询列表
            top_k: 每个查询返回的文档数量
            book_filter: 书籍名称过滤列表，只返回指定书籍中的内容

        返回:
            合并后的文档列表
        """
        all_docs = []

        try:
            print("\n" + "=" * 50)
            print("🔍 从向量数据库检索文档...")
            print("=" * 50)
            
            # 如果有书籍过滤，显示信息
            if book_filter and len(book_filter) > 0:
                print(f"📚 应用书籍过滤: {', '.join(book_filter)}")

            # 遍历每个查询
            for i, query in enumerate(queries):
                print(f"\n查询 {i + 1}: {query}")

                # 从密集向量数据库检索
                if self.milvus_client:
                    try:
                        dense_results = self.milvus_client.Find_Information(
                            query, 
                            top_k=top_k, 
                            book_filter=book_filter  # 传递书籍过滤参数
                        )
                        dense_docs = self.process_dense_results(dense_results)
                        all_docs.extend(dense_docs)
                        print(f"  ✓ 密集向量检索: 找到 {len(dense_docs)} 条结果")
                    except Exception as e:
                        print(f"  ✗ 密集向量检索失败: {str(e)}")

                # 从稀疏向量数据库检索
                if self.elasticsearch_client:
                    try:
                        sparse_results = self.elasticsearch_client.search_sparse(
                            query, 
                            top_k=top_k,
                            book_filter=book_filter  # 传递书籍过滤参数
                        )
                        sparse_docs = self.process_sparse_results(sparse_results)
                        all_docs.extend(sparse_docs)
                        print(f"  ✓ 稀疏向量检索: 找到 {len(sparse_docs)} 条结果")
                    except Exception as e:
                        print(f"  ✗ 稀疏向量检索失败: {str(e)}")

            print(f"\n✅ 共检索到 {len(all_docs)} 条结果")

            # 打印检索结果来源统计
            dense_count = sum(1 for doc in all_docs if doc["source"] == "dense")
            sparse_count = sum(1 for doc in all_docs if doc["source"] == "sparse")
            print(f"📊 结果来源分布: 密集向量 {dense_count} 条, 稀疏向量 {sparse_count} 条")

            return all_docs

        except Exception as e:
            print(f"❌ 文档检索失败: {str(e)}")
            return []

    def rank_documents(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        使用LLM对文档进行相关性排序

        参数:
            query: 原始查询
            docs: 文档列表
            top_n: 要返回的文档数量

        返回:
            排序后的文档列表
        """
        try:
            # 如果文档数量小于等于要求的数量，直接返回所有文档
            if len(docs) <= top_n:
                return docs

            print("\n" + "=" * 50)
            print("🧠 使用LLM对文档进行相关性排序...")
            print("=" * 50)

            # 准备文档内容，为每个文档添加编号
            doc_texts = []
            for i, doc in enumerate(docs):
                doc_text = f"文档[{i + 1}]: "
                if doc["is_image"]:
                    doc_text += "[图像描述] "
                doc_text += doc["text"]
                if doc["page_number"]:
                    doc_text += f" (页码: {doc['page_number']})"
                doc_text += f" [来源: {doc['source']}]"
                doc_texts.append(doc_text)

            # 将所有文档合并为一个字符串
            all_docs_text = "\n\n".join(doc_texts)

            # 使用提示词模板
            inputs = {
                "query": query,
                "docs": all_docs_text,
                "top_n": top_n
            }

            # 调用LLM模型进行文档筛选
            response = ChatBase.invoke(doc_processor_prompt.format_messages(**inputs))
            result_text = response.content

            print(f"LLM排序结果: {result_text}")

            # 解析返回的JSON数组
            import re
            import json

            # 尝试提取JSON数组
            json_match = re.search(r'\[.*?\]', result_text)
            if json_match:
                try:
                    selected_indices = json.loads(json_match.group())
                    # 确保索引在有效范围内
                    valid_indices = [idx for idx in selected_indices if 1 <= idx <= len(docs)]

                    # 如果没有有效索引，返回按得分排序的前top_n个文档
                    if not valid_indices:
                        print("⚠️ LLM未返回有效索引，使用得分排序的前几个文档")
                        docs.sort(key=lambda x: x["score"], reverse=True)
                        return docs[:top_n]

                    # 获取选中的文档
                    selected_docs = [docs[idx - 1] for idx in valid_indices if idx <= len(docs)]

                    print(f"✅ 成功筛选出{len(selected_docs)}个相关文档")

                    # 打印筛选后的文档来源分布
                    dense_selected = sum(1 for doc in selected_docs if doc["source"] == "dense")
                    sparse_selected = sum(1 for doc in selected_docs if doc["source"] == "sparse")
                    print(f"📊 筛选结果分布: 密集向量 {dense_selected} 条, 稀疏向量 {sparse_selected} 条")

                    return selected_docs

                except json.JSONDecodeError:
                    print("⚠️ 无法解析LLM返回的JSON，使用得分排序的前几个文档")
            else:
                print("⚠️ LLM返回格式不符合预期，使用得分排序的前几个文档")

            # 如果解析失败，返回按得分排序的前top_n个文档
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

        except Exception as e:
            print(f"❌ 文档排序失败: {str(e)}")
            # 发生错误时，返回按得分排序的前top_n个文档
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

    async def document_assistant_stream(self, query: str, top_k: int = 5, top_n: int = 5, book_filter: List[str] = None):
        """
        流式文档助手：生成相关问题，检索文档，排序文档，并发送进度更新

        参数:
            query: 原始问题
            top_k: 每个查询检索的文档数量
            top_n: 最终返回的文档数量
            book_filter: 书籍名称过滤列表，只返回指定书籍中的内容

        返回:
            生成器，产生进度更新和最终文档列表
        """
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

            # 更新步骤详情
            step1["details"] = f"生成了{len(related_questions)}个相关问题：\n" + "\n".join([f"• {q}" for q in related_questions[:3]])
            if len(related_questions) > 3:
                step1["details"] += f"\n• 等共{len(related_questions)}个问题"
            yield {"status": "thinking_update", "step": step1}

            # 将原始问题添加到查询列表中
            all_queries = [query] + related_questions

            # 2. 使用所有查询检索文档，传递书籍过滤
            step2 = {
                "icon": "📚",
                "title": "检索相关文档",
                "details": f"从{'、'.join(book_filter) if book_filter else '所有典籍'}中检索相关文档"
            }
            thinking_steps.append(step2)
            yield {"status": "thinking_step", "step": step2}

            all_docs = self.retrieve_documents(all_queries, top_k, book_filter)

            # 更新检索结果
            dense_count = sum(1 for doc in all_docs if doc["source"] == "dense")
            sparse_count = sum(1 for doc in all_docs if doc["source"] == "sparse")
            step2["details"] = f"检索到{len(all_docs)}条文档：密集向量{dense_count}条，稀疏向量{sparse_count}条"
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

            # 更新排序结果
            step3["details"] = f"筛选出{len(ranked_docs)}条最相关的文档用于回答"
            yield {"status": "thinking_update", "step": step3}

            yield {"status": "complete", "documents": ranked_docs, "thinking_steps": thinking_steps}

        except Exception as e:
            print(f"❌ 文档助手处理失败: {str(e)}")
            yield {"status": "error", "error": str(e), "thinking_steps": thinking_steps}

    async def rank_documents_async(self, query: str, docs: List[Dict], top_n: int = 5) -> List[Dict]:
        """
        异步版本的文档排序方法
        """
        try:
            # 如果文档数量小于等于要求的数量，直接返回所有文档
            if len(docs) <= top_n:
                return docs

            print("\n" + "=" * 50)
            print("🧠 使用LLM对文档进行相关性排序...")
            print("=" * 50)

            # 准备文档内容，为每个文档添加编号
            doc_texts = []
            for i, doc in enumerate(docs):
                doc_text = f"文档[{i + 1}]: "
                if doc["is_image"]:
                    doc_text += "[图像描述] "
                doc_text += doc["text"]
                if doc["page_number"]:
                    doc_text += f" (页码: {doc['page_number']})"
                doc_text += f" [来源: {doc['source']}]"
                doc_texts.append(doc_text)

            # 将所有文档合并为一个字符串
            all_docs_text = "\n\n".join(doc_texts)

            # 使用提示词模板
            inputs = {
                "query": query,
                "docs": all_docs_text,
                "top_n": top_n
            }

            # 异步调用LLM模型进行文档筛选
            import asyncio
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: ChatBase.invoke(doc_processor_prompt.format_messages(**inputs))
            )
            result_text = response.content

            print(f"LLM排序结果: {result_text}")

            # 解析返回的JSON数组
            import re
            import json

            # 尝试提取JSON数组
            json_match = re.search(r'\[.*?\]', result_text)
            if json_match:
                try:
                    selected_indices = json.loads(json_match.group())
                    # 确保索引在有效范围内
                    valid_indices = [idx for idx in selected_indices if 1 <= idx <= len(docs)]

                    # 如果没有有效索引，返回按得分排序的前top_n个文档
                    if not valid_indices:
                        print("⚠️ LLM未返回有效索引，使用得分排序的前几个文档")
                        docs.sort(key=lambda x: x["score"], reverse=True)
                        return docs[:top_n]

                    # 获取选中的文档
                    selected_docs = [docs[idx - 1] for idx in valid_indices if idx <= len(docs)]

                    print(f"✅ 成功筛选出{len(selected_docs)}个相关文档")

                    # 打印筛选后的文档来源分布
                    dense_selected = sum(1 for doc in selected_docs if doc["source"] == "dense")
                    sparse_selected = sum(1 for doc in selected_docs if doc["source"] == "sparse")
                    print(f"📊 筛选结果分布: 密集向量 {dense_selected} 条, 稀疏向量 {sparse_selected} 条")

                    return selected_docs

                except json.JSONDecodeError:
                    print("⚠️ 无法解析LLM返回的JSON，使用得分排序的前几个文档")
            else:
                print("⚠️ LLM返回格式不符合预期，使用得分排序的前几个文档")

            # 如果解析失败，返回按得分排序的前top_n个文档
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

        except Exception as e:
            print(f"❌ 文档排序失败: {str(e)}")
            # 发生错误时，返回按得分排序的前top_n个文档
            docs.sort(key=lambda x: x["score"], reverse=True)
            return docs[:top_n]

    async def rag_stream(self, state: dict):
        """
        真正的流式节点：每次从 astream 生成部分内容后 yield 出去
        """
        try:
            # 适应不同的参数命名方式
            query = state.get("content", state.get("query", ""))
            admin = state["admin"]
            chat_history = state["chat_history"]
            top_k = state.get("top_k", 5)
            top_n = min(top_k, 5)  # 最终返回的文档数量
            book_filter = state.get("books", [])  # 获取书籍过滤参数

            # 使用流式文档助手处理，传递书籍过滤参数
            filtered_docs = None
            thinking_steps = []

            async for doc_update in self.document_assistant_stream(query, top_k, top_n, book_filter):
                print(f"🔍 收到文档助手更新: {doc_update}")
                if doc_update["status"] == "thinking_step":
                    # 新的思考步骤
                    step = doc_update["step"]
                    thinking_steps.append(step)
                    print(f"📝 发送思考步骤: {step}")
                    yield {"thinking_step": step}
                elif doc_update["status"] == "thinking_update":
                    # 更新思考步骤
                    print(f"🔄 发送思考步骤更新: {doc_update['step']}")
                    yield {"thinking_update": doc_update["step"]}
                elif doc_update["status"] == "complete":
                    # 获取最终文档列表和完整思考步骤
                    filtered_docs = doc_update["documents"]
                    if "thinking_steps" in doc_update:
                        thinking_steps = doc_update["thinking_steps"]
                    print(f"✅ 文档处理完成，思考步骤数量: {len(thinking_steps)}")
                    break
                elif doc_update["status"] == "error":
                    # 处理错误
                    yield {"partial_result": f"❌ 文档处理出错: {doc_update['error']}"}
                    return

            if not filtered_docs:
                yield {"partial_result": "❌ 未能获取到相关文档"}
                return

            # 格式化上下文
            formatted_context = self.format_context(filtered_docs)

            print(f"✅ 文档处理完成，筛选出 {len(filtered_docs)} 个最相关文档")

            # 构建输入 - 适配不同格式的聊天历史
            inputs = {
                "admin": admin,
                "query": query,
                "context": formatted_context
            }

            # 处理聊天历史数据 - 确保格式正确
            # 检查聊天历史是否已经是 LangChain 消息列表
            if hasattr(chat_history, 'messages'):
                # 如果是 RedisChatMessageHistory 对象
                inputs["history"] = chat_history.messages
            elif isinstance(chat_history, list):
                # 如果是消息列表，需要转换为 LangChain 消息格式
                messages = []
                try:
                    for msg in chat_history:
                        if isinstance(msg, dict) and "role" in msg and "content" in msg:
                            if msg["role"] == "user":
                                messages.append(HumanMessage(content=msg["content"]))
                            elif msg["role"] == "assistant":
                                messages.append(AIMessage(content=msg["content"]))
                    inputs["history"] = messages
                    print(f"转换后的消息数量: {len(messages)}")
                except Exception as e:
                    print(f"转换消息时发生错误: {e}")
                    # 如果转换失败，使用空消息列表
                    inputs["history"] = []
            else:
                # 不是预期的格式，使用空消息列表
                print(f"无法处理的聊天历史格式，使用空消息列表")
                inputs["history"] = []

            # 发送思考步骤完成信息和开始生成答案的信号
            yield {"thinking_complete": True, "thinking_steps": thinking_steps}

            full_text = ""
            print("🤖 进入流式生成")

            try:
                async for chunk in self.rag_chain.astream(inputs):
                    content = getattr(chunk, "content", str(chunk))
                    full_text += content

                    # 每一步都 yield 部分内容，供前端实时消费
                    yield {"partial_result": content}

                # 注意: 这里不再更新历史记录
                # 历史记录的更新由main.py中的RAG_ask_stream函数统一处理
                # 这避免了重复更新Redis历史记录的问题

                yield {
                    "result": full_text
                }
            except Exception as e:
                print(f"生成回答时发生错误: {e}")
                # 返回错误信息
                yield {
                    "error": f"生成回答时发生错误: {str(e)}",
                    "partial_result": f"抱歉，在处理您的问题时遇到了技术问题: {str(e)}"
                }

        except Exception as e:
            print(f"RAG流处理时发生错误: {e}")
            yield {
                "error": f"处理请求时发生错误: {str(e)}",
                "partial_result": "抱歉，在处理您的请求时遇到了技术问题。"
            }

    # ──────────────────────────────────────────
    #  ReAct Agent 流式输出（新版）
    # ──────────────────────────────────────────

    async def react_stream(self, state: dict):
        """
        使用 ReAct Agent 进行流式推理和回答
        替代原有的 rag_stream 固定流水线
        """
        async for chunk in self.react_agent.react_stream(state):
            yield chunk

