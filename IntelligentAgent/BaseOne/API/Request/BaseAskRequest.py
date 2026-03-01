from pydantic import BaseModel  # is  定义请求和响应的数据结构（即"数据模型"），并自动进行类型校验、格式转换、错误提示等。
from typing import List


class AskRequest(BaseModel):# is 请求体
    session_id: str
    admin: str
    content: str  # 用户输入的消息内容，替代原来的topic字段
    books: List[str]
