from langchain_openai import ChatOpenAI
from .api_keys import APIkey, APIUrl, model

ChatBase = ChatOpenAI(
    api_key=APIkey,
    base_url=APIUrl,
    model=model,
    streaming=True,
)
