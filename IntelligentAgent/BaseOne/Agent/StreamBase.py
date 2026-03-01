from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from ..utils.llms import ChatBase
from ..Prompts.MyPrompt import system_prompt, human_prompt
import asyncio
import json


class StreamAgent:
    def __init__(self, redis_url, session_id):
        # 构建 Prompt 模板
        self.prompt = ChatPromptTemplate.from_messages([
            system_prompt,
            MessagesPlaceholder("history"),
            human_prompt
        ])
        self.chain = self.prompt | ChatBase

        # 初始化聊天记录
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

        # 创建图结构
        self.graph = self._build_graph()

    # 新增流式处理节点
    async def _node_worker_stream(self, state: dict) -> dict:
        content = state["content"]  # 使用content替代topic
        admin = state["admin"]
        chat_history = state["chat_history"]

        inputs = {
            "history": chat_history.messages,
            "topic": content,  # 内部仍使用topic键，但值来自content
            "admin": admin
        }

        full_text = ""
        for chunk in await asyncio.to_thread(lambda: list(self.chain.stream(inputs))):
            content = getattr(chunk, "content", str(chunk))
            full_text += content

        # 更新历史记录
        chat_history.add_user_message(content)
        chat_history.add_ai_message(full_text)

        return {"result": full_text, "chat_history": chat_history}

    def _build_graph(self):
        graph = StateGraph(dict)
        graph.add_node("AskNode", self._node_worker_stream)
        graph.set_entry_point("AskNode")
        graph.set_finish_point("AskNode")
        return graph.compile()

    async def ask_stream(self, content: str, admin: str):
        """执行提问并以流形式返回结果"""
        # 直接使用底层LLM的流式输出，不经过LangGraph
        inputs = {
            "history": self.history.messages,
            "topic": content,  # 内部仍使用topic键，但值来自content
            "admin": admin
        }

        full_text = ""

        # 使用LLM的流式输出
        async for chunk in await asyncio.to_thread(lambda: self.chain.astream(inputs)):
            content_chunk = getattr(chunk, "content", str(chunk))
            if content_chunk:
                full_text += content_chunk
                # 确保输出的是JSON格式的字符串，方便前端解析
                yield json.dumps({"content": content_chunk})

        # 更新历史记录
        self.history.add_user_message(content)
        self.history.add_ai_message(full_text)
