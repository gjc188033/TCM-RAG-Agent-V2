import os
import json
import asyncio
from ..utils.llms import ChatBase
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import RedisChatMessageHistory
from ..Prompts.MyPrompt import system_prompt, human_prompt

class BaseAsk:
    def __init__(self, redis_url, session_id):
        # 创建提示模板
        self.prompt = ChatPromptTemplate.from_messages(
            [system_prompt, MessagesPlaceholder("history"), human_prompt])
        
        # 创建聊天链
        self.chain = self.prompt | ChatBase

        # 初始化聊天历史
        self.history = RedisChatMessageHistory(session_id=session_id, url=redis_url)

    async def ask(self, question, admin="AI专员"):
        """
        向大模型提问并获取回答
        
        参数:
            question (str): 用户问题
            admin (str): 专业领域标识
            
        返回:
            str: 模型回答
        """
        # 构建输入
        inputs = {
            "admin": admin,
            "history": self.history.messages,
            "query": question
        }

        # 获取回答
        response = await self.chain.ainvoke(inputs)
        answer = response.content

        # 更新历史记录
        self.history.add_user_message(question)
        self.history.add_ai_message(answer)

        return answer
    
    async def stream_ask(self, question, admin="AI专员"):
        """
        流式回答用户问题
        
        参数:
            question (str): 用户问题
            admin (str): 专业领域标识
            
        返回:
            生成器: 流式的回答内容
        """
        # 构建输入
        inputs = {
            "admin": admin,
            "history": self.history.messages,
            "query": question
        }
        
        full_response = ""
        
        # 流式获取回答
        async for chunk in self.chain.astream(inputs):
            content = getattr(chunk, "content", str(chunk))
            full_response += content
            yield json.dumps({"content": content})
        
        # 更新历史记录
        self.history.add_user_message(question)
        self.history.add_ai_message(full_response)
        
        # 发送结束标志
        yield json.dumps({"type": "end"}) 