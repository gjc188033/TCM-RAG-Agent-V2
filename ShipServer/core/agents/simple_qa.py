import os
import json
import asyncio
from ..foundation.llm_client import ChatBase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from ..templates.prompt_registry import system_prompt, human_prompt

class BaseAsk:
    def __init__(self, redis_url, session_id):
        self.prompt = ChatPromptTemplate.from_messages(
            [system_prompt, MessagesPlaceholder("history"), human_prompt])
        self.chain = self.prompt | ChatBase
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

    async def ask(self, question, admin="AI专员"):
        inputs = {
            "admin": admin,
            "history": self.history.messages,
            "query": question
        }
        response = await self.chain.ainvoke(inputs)
        answer = response.content
        self.history.add_user_message(question)
        self.history.add_ai_message(answer)
        return answer
    
    async def stream_ask(self, question, admin="AI专员"):
        inputs = {
            "admin": admin,
            "history": self.history.messages,
            "query": question
        }
        full_response = ""
        async for chunk in self.chain.astream(inputs):
            content = getattr(chunk, "content", str(chunk))
            full_response += content
            yield json.dumps({"content": content})
        self.history.add_user_message(question)
        self.history.add_ai_message(full_response)
        yield json.dumps({"type": "end"})
