import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from core.schemas.request.query_schema import AskRequest
from core.schemas.request.conversation_schema import (ConversationCreateRequest,ConversationDeleteRequest,ConversationListRequest,ConversationResponse,ConversationUpdateTitleRequest)
from core.agents.stream_handler import StreamAgent
from core.agents.retrieval.retrieval_orchestrator import RagAgent
from core.agents.retrieval.es_client import ElasticsearchDB
from core.agents.retrieval.pg_terminology import TerminologyDB
from core.agents.retrieval.vector_encoder import SpladeEmbedding
from core.session.session_store import ConversationManager
from langchain_community.chat_message_histories import RedisChatMessageHistory
from typing import AsyncGenerator, List, Optional, Dict, Any
from fastapi.responses import StreamingResponse, JSONResponse
import time
from datetime import datetime
import json
import threading
import asyncio

app = FastAPI()

# 添加CORS配置，允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis配置
REDIS_URL = "redis://10.28.124.91:6379"

# 创建智能体（共享 redis 历史记录）
agent_pool = {}

# 创建会话管理器
conversation_manager = ConversationManager(redis_url=REDIS_URL)

# 模型加载状态
model_status = {
    "elasticsearch_loaded": False,
    "sparse_embedding_loaded": False,
    "terminology_db_loaded": False,
    "rag_ready": False,
    "loading_message": "正在初始化船代知识库..."
}

# 预加载的客户端
global_elasticsearch_client = None
global_terminology_client = None


# 预加载Elasticsearch和嵌入模型
def preload_elasticsearch():
    global global_elasticsearch_client, model_status
    try:
        print("开始预加载Elasticsearch和嵌入模型...")
        model_status["loading_message"] = "正在连接Elasticsearch知识库..."

        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                global_elasticsearch_client = ElasticsearchDB()
                print("✅ Elasticsearch连接成功")
                model_status["elasticsearch_loaded"] = True
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                print(f"Elasticsearch连接失败，尝试重连 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(2)

        model_status["loading_message"] = "正在加载稀疏嵌入模型..."

        try:
            result = global_elasticsearch_client.search_sparse("预热查询", top_k=1)
            model_status["sparse_embedding_loaded"] = True
            print("✅ 稀疏嵌入模型加载完成")
        except Exception as e:
            print(f"❌ 稀疏嵌入模型预热失败: {str(e)}")
            model_status["sparse_embedding_loaded"] = True
            model_status["loading_message"] = f"稀疏嵌入模型预热失败: {str(e)}"

        check_rag_ready()
        print("Elasticsearch和嵌入模型加载完成!")
    except Exception as e:
        error_msg = f"Elasticsearch加载失败: {str(e)}"
        model_status["loading_message"] = error_msg
        print(f"❌ {error_msg}")
        model_status["elasticsearch_loaded"] = True
        model_status["sparse_embedding_loaded"] = True
        check_rag_ready()


# 预加载PostgreSQL术语库
def preload_terminology():
    global global_terminology_client, model_status
    try:
        print("开始预加载PostgreSQL术语库...")
        model_status["loading_message"] = "正在连接术语库..."

        global_terminology_client = TerminologyDB()
        if global_terminology_client.is_connected:
            model_status["terminology_db_loaded"] = True
            print("✅ 术语库连接成功")
        else:
            print("⚠️ 术语库连接失败，系统将降级运行")
            model_status["terminology_db_loaded"] = True

        check_rag_ready()
    except Exception as e:
        error_msg = f"术语库加载失败: {str(e)}"
        print(f"⚠️ {error_msg}")
        model_status["terminology_db_loaded"] = True
        check_rag_ready()


# 检查RAG是否就绪
def check_rag_ready():
    global model_status
    if (model_status["elasticsearch_loaded"] and
        model_status["sparse_embedding_loaded"] and
        model_status["terminology_db_loaded"]):
        model_status["rag_ready"] = True
        model_status["loading_message"] = "船代知识库加载完成"
        print("所有模型加载完成，系统已就绪!")


# 获取模型状态API
@app.get("/model_status")
async def get_model_status():
    return model_status


@app.post("/booksname")
async def get_available_sources():
    """获取可用的知识库来源列表"""
    global global_elasticsearch_client
    temp = global_elasticsearch_client.get_all_source_names()
    print(temp)
    return temp


@app.post("/conversations/{session_id}/messages/ragstream")
async def RAG_ask_stream(session_id: str, req: AskRequest):
    print(f"收到发送消息请求，会话ID: {session_id}, 内容长度: {len(req.content)}")
    print(f"请求内容: {req}")

    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        print(f"警告: 会话ID {session_id} 不存在")
    else:
        print(f"会话ID {session_id} 有效，标题: {conversation['title']}")

    if not model_status["rag_ready"]:
        return JSONResponse(
            status_code=503,
            content={"error": "船代知识库正在加载中", "message": model_status["loading_message"]}
        )

    req.session_id = session_id

    conversation_manager.update_conversation_message(req.session_id, req.content, is_user=True)

    redis_history = RedisChatMessageHistory(session_id=session_id, url=REDIS_URL)

    try:
        agent = RagAgent(
            redis_url=REDIS_URL,
            session_id=req.session_id,
            elasticsearch_client=global_elasticsearch_client,
            terminology_client=global_terminology_client
        )
    except Exception as e:
        error_msg = f"创建RAG代理失败: {str(e)}"
        print(error_msg)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg, "message": "船代知识库初始化失败"}
        )

    async def stream_generator():
        """简单的流式响应生成器"""
        full_response = ""
        try:
            messages = conversation_manager.get_conversation_messages(req.session_id)
            print(f"获取到 {len(messages)} 条历史消息用于RAG")

            if req.books and len(req.books) > 0:
                print(f"用户选择的知识库来源: {', '.join(req.books)}")
            else:
                print("用户未选择特定来源，将搜索全部知识库")

            info = {
                "query": req.content,
                "admin": req.admin,
                "chat_history": messages,
                "books": req.books,
                "top_k": 20,
                "max_iterations": 6,
            }

            async for chunk in agent.react_stream(info):
                try:
                    if "partial_result" in chunk:
                        content_value = chunk["partial_result"]
                        if content_value:
                            chunk_str = json.dumps({"content": content_value, "status": "generating"})
                            yield f"data: {chunk_str}\n\n"
                            full_response += content_value
                    elif "thinking_step" in chunk:
                        step_data = json.dumps({"thinking_step": chunk["thinking_step"]})
                        yield f"data: {step_data}\n\n"
                    elif "thinking_update" in chunk:
                        update_data = json.dumps({"thinking_update": chunk["thinking_update"]})
                        yield f"data: {update_data}\n\n"
                    elif "thinking_complete" in chunk:
                        complete_data = json.dumps({
                            "thinking_complete": chunk["thinking_complete"],
                            "thinking_steps": chunk.get("thinking_steps", [])
                        })
                        yield f"data: {complete_data}\n\n"
                    elif "result" in chunk:
                        full_response = chunk["result"]
                    elif "error" in chunk:
                        error_chunk = json.dumps({"content": f"处理出错: {chunk['error']}", "status": "error"})
                        yield f"data: {error_chunk}\n\n"
                        return
                except Exception as e:
                    print(f"处理chunk时出错: {str(e)}")
                    continue

            yield f"data: {json.dumps({'content': '', 'status': 'complete'})}\n\n"

            conversation_manager.update_conversation_message(req.session_id, full_response, is_user=False)
            redis_history.add_user_message(req.content)
            redis_history.add_ai_message(full_response)

        except Exception as e:
            error_msg = f"RAG流处理异常: {str(e)}"
            print(error_msg)
            error_chunk = json.dumps({"content": f"处理异常: {str(e)}", "status": "error"})
            yield f"data: {error_chunk}\n\n"

    response = StreamingResponse(stream_generator(), media_type="text/event-stream")
    response.headers["X-Session-ID"] = session_id
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response


# 会话管理接口

@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreateRequest):
    """创建新的会话"""
    print(f"接收到创建会话请求，标题: {req.title}")
    conversation = conversation_manager.create_conversation(req.title)
    print(f"会话创建成功，ID: {conversation['session_id']}")
    conversation["created_at"] = datetime.fromtimestamp(conversation["created_at"]).isoformat()
    return conversation


@app.delete("/conversations/{session_id}")
async def delete_conversation(session_id: str):
    """删除指定的会话"""
    success = conversation_manager.delete_conversation(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="会话不存在")
    return {"success": True, "message": "会话已删除"}


@app.get("/conversations", response_model=List[ConversationResponse])
async def list_conversations(page: int = 1, page_size: int = 20):
    """获取会话列表"""
    conversations = conversation_manager.list_conversations(page, page_size)
    for conv in conversations:
        conv["created_at"] = datetime.fromtimestamp(conv["created_at"]).isoformat()
    return conversations


@app.get("/conversations/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    """获取指定会话的详情"""
    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation["created_at"] = datetime.fromtimestamp(conversation["created_at"]).isoformat()
    return conversation


@app.get("/conversations/{session_id}/messages")
async def get_conversation_messages(session_id: str):
    """获取指定会话的所有消息"""
    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    messages = conversation_manager.get_conversation_messages(session_id)
    for msg in messages:
        if not msg["timestamp"]:
            msg["timestamp"] = datetime.now().isoformat()

    return messages


@app.put("/conversations/{session_id}/title", response_model=ConversationResponse)
async def update_conversation_title(session_id: str, req: ConversationUpdateTitleRequest):
    """更新会话标题"""
    conversation = conversation_manager.update_conversation_title(session_id, req.title)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    conversation["created_at"] = datetime.fromtimestamp(conversation["created_at"]).isoformat()
    return conversation


@app.on_event("startup")
async def startup_event():
    """启动时进行初始化操作"""
    threading.Thread(target=preload_elasticsearch, daemon=True).start()
    threading.Thread(target=preload_terminology, daemon=True).start()


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=9978)
