from pydantic import BaseModel
from typing import Optional, List


class ConversationCreateRequest(BaseModel):
    """创建会话的请求模型"""
    title: str = "新对话"  # 会话标题，默认为"新对话"


class ConversationDeleteRequest(BaseModel):
    """删除会话的请求模型"""
    session_id: str  # 要删除的会话ID


class ConversationListRequest(BaseModel):
    """获取会话列表的请求模型"""
    page: int = 1  # 页码，默认第一页
    page_size: int = 20  # 每页数量，默认20条


class ConversationUpdateTitleRequest(BaseModel):
    """更新会话标题的请求模型"""
    title: str  # 新的会话标题


class ConversationResponse(BaseModel):
    """会话信息响应模型"""
    session_id: str  # 会话ID
    title: str  # 会话标题
    created_at: str  # 创建时间
    last_message: Optional[str] = None  # 最后一条消息（可选）
    message_count: int = 0  # 消息数量 