from langchain_openai import ChatOpenAI
from .config import APIkey, APIUrl, model

ChatBase = ChatOpenAI(
    api_key=APIkey,
    base_url=APIUrl,
    model=model,
    streaming=True,
)
