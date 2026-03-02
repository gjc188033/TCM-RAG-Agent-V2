from pydantic import BaseModel
from typing import Optional, List


class ConversationCreateRequest(BaseModel):
    """创建会话的请求模型"""
    title: str = "新对话"


class ConversationDeleteRequest(BaseModel):
    """删除会话的请求模型"""
    session_id: str


class ConversationListRequest(BaseModel):
    """获取会话列表的请求模型"""
    page: int = 1
    page_size: int = 20


class ConversationUpdateTitleRequest(BaseModel):
    """更新会话标题的请求模型"""
    title: str


class ConversationResponse(BaseModel):
    """会话信息响应模型"""
    session_id: str
    title: str
    created_at: str
    last_message: Optional[str] = None
    message_count: int = 0
