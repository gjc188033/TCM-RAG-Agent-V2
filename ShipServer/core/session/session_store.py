import redis
import json
import time
from typing import List, Dict, Optional, Any
import uuid
from langchain_community.chat_message_histories import RedisChatMessageHistory


class ConversationManager:
    """会话管理器，负责处理Redis中的会话数据"""

    def __init__(self, redis_url: str):
        """初始化会话管理器
        
        Args:
            redis_url: Redis连接URL
        """
        self.redis_client = redis.from_url(redis_url)
        self.redis_url = redis_url
        self.conversation_list_key = "conversation_list"  # 存储会话列表的键

    def create_conversation(self, title: str = "新对话") -> Dict[str, Any]:
        """创建新的会话
        
        Args:
            title: 会话标题
            
        Returns:
            包含会话信息的字典
        """
        # 生成唯一的会话ID
        session_id = f"session_{str(uuid.uuid4())}"  # is 这里的f表示字符串格式化，也就是把session_拼接在uuid后面
        timestamp = int(time.time())

        # 创建会话信息
        conversation = {
            "session_id": session_id,
            "title": title,
            "created_at": timestamp,
            "last_message": None,
            "message_count": 0
        }

        # 序列化会话信息
        conversation_json = json.dumps(conversation)

        # 创建会话详情记录
        self.redis_client.hset(
            f"conversation:{session_id}",
            mapping={
                "title": title,
                "created_at": timestamp,
                "last_message": "",
                "message_count": 0
            }
        )

        # 添加到会话列表，使用有序集合按创建时间排序
        self.redis_client.zadd(self.conversation_list_key, {session_id: timestamp})

        # 创建一个空的消息历史记录 (由LangChain的RedisChatMessageHistory管理)
        RedisChatMessageHistory(session_id=session_id, url=self.redis_url)

        return {
            "session_id": session_id,
            "title": title,
            "created_at": timestamp,
            "last_message": None,
            "message_count": 0
        }

    def delete_conversation(self, session_id: str) -> bool:
        """删除指定的会话
        
        Args:
            session_id: 会话ID
            
        Returns:
            是否成功删除
        """
        # 检查会话是否存在
        if not self.redis_client.exists(f"conversation:{session_id}"):
            return False

        # 从会话列表中删除
        self.redis_client.zrem(self.conversation_list_key, session_id)

        # 删除会话详情
        self.redis_client.delete(f"conversation:{session_id}")

        # 删除消息历史记录
        history_key = f"message_store:{session_id}"
        self.redis_client.delete(history_key)

        return True

    def get_conversation(self, session_id: str) -> Optional[Dict[str, Any]]:
        """获取指定会话的详情
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话信息字典，不存在则返回None
        """
        # 检查会话是否存在
        if not self.redis_client.exists(f"conversation:{session_id}"):
            return None

        # 获取会话信息
        conversation_data = self.redis_client.hgetall(f"conversation:{session_id}")

        if not conversation_data:
            return None

        # 转换数据类型
        return {
            "session_id": session_id,
            "title": conversation_data.get(b'title', b'').decode('utf-8'),
            "created_at": int(conversation_data.get(b'created_at', 0)),
            "last_message": conversation_data.get(b'last_message', b'').decode('utf-8') or None,
            "message_count": int(conversation_data.get(b'message_count', 0))
        }

    def list_conversations(self, page: int = 1, page_size: int = 20) -> List[Dict[str, Any]]:
        """获取会话列表
        
        Args:
            page: 页码，从1开始
            page_size: 每页数量
            
        Returns:
            会话信息列表
        """
        # 计算分页参数
        start = (page - 1) * page_size
        end = start + page_size - 1

        # 获取会话ID列表，按创建时间倒序排列
        session_ids = self.redis_client.zrevrange(self.conversation_list_key, start, end)

        # 获取每个会话的详细信息
        conversations = []
        for session_id in session_ids:
            session_id_str = session_id.decode('utf-8')
            conversation = self.get_conversation(session_id_str)
            if conversation:
                conversations.append(conversation)

        return conversations

    def update_conversation_message(self, session_id: str, message_text: str, is_user: bool = True) -> bool:
        """更新会话的最后消息和消息计数
        
        Args:
            session_id: 会话ID
            message_text: 消息内容
            is_user: 是否是用户消息
            
        Returns:
            是否成功更新
        """
        # 检查会话是否存在
        if not self.redis_client.exists(f"conversation:{session_id}"):
            return False

        # 更新消息计数
        self.redis_client.hincrby(f"conversation:{session_id}", "message_count", 1)

        # 如果是用户消息且标题为默认的"新对话"，则用第一条用户消息更新标题
        if is_user:
            title = self.redis_client.hget(f"conversation:{session_id}", "title")
            if title and title.decode('utf-8') == "新对话":
                # 截取前30个字符作为标题
                new_title = message_text[:30] + ("..." if len(message_text) > 30 else "")
                self.redis_client.hset(f"conversation:{session_id}", "title", new_title)

        # 更新最后一条消息
        shortened_message = message_text[:50] + ("..." if len(message_text) > 50 else "")
        self.redis_client.hset(f"conversation:{session_id}", "last_message", shortened_message)

        return True

    def update_conversation_title(self, session_id: str, new_title: str) -> Optional[Dict[str, Any]]:
        """更新会话标题
        
        Args:
            session_id: 会话ID
            new_title: 新的会话标题
            
        Returns:
            更新后的会话信息字典，不存在则返回None
        """
        # 检查会话是否存在
        if not self.redis_client.exists(f"conversation:{session_id}"):
            return None

        # 更新会话标题
        self.redis_client.hset(f"conversation:{session_id}", "title", new_title)

        # 返回更新后的会话信息
        return self.get_conversation(session_id)

    def get_conversation_messages(self, session_id: str) -> List[Dict[str, Any]]:
        """获取指定会话的所有消息
        
        Args:
            session_id: 会话ID
            
        Returns:
            消息列表，每条消息包含角色(role)和内容(content)
        """
        # 检查会话是否存在
        if not self.redis_client.exists(f"conversation:{session_id}"):
            return []

        # 调试：只显示消息数量
        history_key = f"message_store:{session_id}"
        raw_data = self.redis_client.lrange(history_key, 0, -1)
        print(f"Redis中有 {len(raw_data)} 条原始消息记录")

        # 使用LangChain的RedisChatMessageHistory获取消息
        history = RedisChatMessageHistory(session_id=session_id, url=self.redis_url)

        # 将LangChain消息格式转换为我们的API格式
        messages = []
        for msg in history.messages:
            role = "user" if msg.type == "human" else "assistant"
            messages.append({
                "role": role,
                "content": msg.content,
                "timestamp": ""  # Redis中没有存储时间戳，所以这里留空
            })

        return messages
