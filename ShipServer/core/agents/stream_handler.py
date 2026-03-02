from langgraph.graph import StateGraph
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from ..foundation.llm_client import ChatBase
from ..templates.prompt_registry import system_prompt, human_prompt
import asyncio
import json


class StreamAgent:
    def __init__(self, redis_url, session_id):
        self.prompt = ChatPromptTemplate.from_messages([
            system_prompt,
            MessagesPlaceholder("history"),
            human_prompt
        ])
        self.chain = self.prompt | ChatBase
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)
        self.graph = self._build_graph()

    async def _node_worker_stream(self, state: dict) -> dict:
        content = state["content"]
        admin = state["admin"]
        chat_history = state["chat_history"]

        inputs = {
            "history": chat_history.messages,
            "topic": content,
            "admin": admin
        }

        full_text = ""
        for chunk in await asyncio.to_thread(lambda: list(self.chain.stream(inputs))):
            content = getattr(chunk, "content", str(chunk))
            full_text += content

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
        inputs = {
            "history": self.history.messages,
            "topic": content,
            "admin": admin
        }

        full_text = ""

        async for chunk in await asyncio.to_thread(lambda: self.chain.astream(inputs)):
            content_chunk = getattr(chunk, "content", str(chunk))
            if content_chunk:
                full_text += content_chunk
                yield json.dumps({"content": content_chunk})

        self.history.add_user_message(content)
        self.history.add_ai_message(full_text)
