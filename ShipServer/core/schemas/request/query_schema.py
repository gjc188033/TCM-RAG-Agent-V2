from pydantic import BaseModel
from typing import List


class AskRequest(BaseModel):
    session_id: str
    admin: str
    content: str
    books: List[str]
