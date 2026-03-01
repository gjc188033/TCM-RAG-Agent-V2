import uvicorn
from fastapi import FastAPI, Response, HTTPException, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.middleware.cors import CORSMiddleware
from BaseOne.API.Request.BaseAskRequest import AskRequest
from BaseOne.API.Request.ConversationRequest import (ConversationCreateRequest,ConversationDeleteRequest,ConversationListRequest,ConversationResponse,ConversationUpdateTitleRequest)
from BaseOne.Agent.StreamBase import StreamAgent
from BaseOne.Agent.Rag.RagAgent import RagAgent
from BaseOne.Agent.Rag.MilvusWoker import MilvusDB
from BaseOne.Agent.Rag.ElasticsearchWoker import ElasticsearchDB
from BaseOne.Agent.Rag.embeddings import SpladeEmbedding
from BaseOne.Agent.Rag.config import MILVUS_URI, MILVUS_USER, MILVUS_PASSWORD, MILVUS_COLLECTION
from BaseOne.Memorys.ConversationManager import ConversationManager
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
    allow_origins=["*"],  # 允许所有来源，生产环境请指定具体域名
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
    "milvus_loaded": False,
    "elasticsearch_loaded": False,
    "dense_embedding_loaded": False,
    "sparse_embedding_loaded": False,
    "rag_ready": False,
    "loading_message": "正在初始化中医数据库模型..."
}

# 预加载的向量数据库客户端
global_milvus_client = None
global_elasticsearch_client = None


# 预加载向量数据库
def preload_milvus():
    global global_milvus_client, model_status
    try:
        print("开始预加载Milvus向量数据库和嵌入模型...")
        model_status["loading_message"] = "正在加载Milvus向量数据库连接..."

        # 尝试连接Milvus
        max_retries = 3
        retry_count = 0
        while retry_count < max_retries:
            try:
                global_milvus_client = MilvusDB(uri=MILVUS_URI, user=MILVUS_USER, password=MILVUS_PASSWORD,collection=MILVUS_COLLECTION)
                print("🔌 连接到Milvus数据库: " + MILVUS_URI)
                print("✅ Milvus连接成功")
                model_status["milvus_loaded"] = True
                break
            except Exception as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise e
                print(f"Milvus连接失败，尝试重连 ({retry_count}/{max_retries}): {str(e)}")
                time.sleep(2)  # 等待2秒后重试

        model_status["loading_message"] = "正在加载稠密嵌入模型..."

        # 尝试预热嵌入模型
        try:
            # 预热嵌入模型，调用一次Find_Information
            global_milvus_client.Find_Information("预热查询", top_k=1)
            model_status["dense_embedding_loaded"] = True
            print("✅ 稠密嵌入模型加载完成")
        except Exception as e:
            print(f"❌ 稠密嵌入模型预热失败: {str(e)}")
            # 即使嵌入模型预热失败，我们也标记为已加载，以便系统可以继续使用Elasticsearch
            model_status["dense_embedding_loaded"] = True
            model_status["loading_message"] = f"稠密嵌入模型预热失败，但系统仍可使用Elasticsearch: {str(e)}"

        # 检查是否可以设置RAG为就绪状态
        check_rag_ready()
        print("Milvus向量数据库和稠密嵌入模型加载完成!")
    except Exception as e:
        error_msg = f"Milvus模型加载失败: {str(e)}"
        model_status["loading_message"] = error_msg
        print(f"❌ {error_msg}")

        # 即使Milvus加载失败，我们也可以继续使用Elasticsearch
        # 将这些标记为已加载，以便系统可以继续运行
        model_status["milvus_loaded"] = True
        model_status["dense_embedding_loaded"] = True

        # 检查是否可以设置RAG为就绪状态（只用Elasticsearch）
        check_rag_ready()


# 预加载Elasticsearch和SPLADE模型
def preload_elasticsearch():
    global global_elasticsearch_client, model_status
    try:
        print("开始预加载Elasticsearch和SPLADE稀疏向量模型...")
        model_status["loading_message"] = "正在加载Elasticsearch数据库连接..."

        # 尝试连接Elasticsearch
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
                time.sleep(2)  # 等待2秒后重试

        model_status["loading_message"] = "正在加载SPLADE稀疏嵌入模型..."

        # 尝试预热SPLADE模型
        try:
            # 预热SPLADE模型，调用一次search_sparse，但不打印结果
            result = global_elasticsearch_client.search_sparse("预热查询", top_k=1)
            model_status["sparse_embedding_loaded"] = True
            print("✅ SPLADE稀疏向量模型加载完成")
        except Exception as e:
            print(f"❌ SPLADE模型预热失败: {str(e)}")
            # 即使SPLADE模型加载失败，我们也标记为已加载，以便系统可以继续使用Milvus
            model_status["sparse_embedding_loaded"] = True
            model_status["loading_message"] = f"SPLADE模型预热失败，但系统仍可使用Milvus: {str(e)}"

        # 检查是否可以设置RAG为就绪状态
        check_rag_ready()
        print("Elasticsearch和SPLADE稀疏向量模型加载完成!")
    except Exception as e:
        error_msg = f"Elasticsearch或SPLADE模型加载失败: {str(e)}"
        model_status["loading_message"] = error_msg
        print(f"❌ {error_msg}")

        # 即使Elasticsearch加载失败，我们也可以继续使用Milvus
        # 将这些标记为已加载，以便系统可以继续运行
        model_status["elasticsearch_loaded"] = True
        model_status["sparse_embedding_loaded"] = True

        # 检查是否可以设置RAG为就绪状态（只用Milvus）
        check_rag_ready()


# 检查RAG是否就绪
def check_rag_ready():
    global model_status
    if (model_status["milvus_loaded"] and
        model_status["elasticsearch_loaded"] and
        model_status["dense_embedding_loaded"] and
        model_status["sparse_embedding_loaded"]):
        model_status["rag_ready"] = True
        model_status["loading_message"] = "中医数据库模型加载完成"
        print("所有RAG模型加载完成，系统已就绪!")


# 获取模型状态API
@app.get("/model_status")
async def get_model_status():
    return model_status

# 获取数据库统计信息API

@app.post("/booksname")
async def get_available_books():
    global global_elasticsearch_client
    temp=global_elasticsearch_client.get_all_book_names()
    print(temp)
    return  temp


@app.post("/conversations/{session_id}/messages/ragstream")
async def RAG_ask_stream(session_id: str, req: AskRequest):
    print(f"收到发送消息请求，会话ID: {session_id}, 内容长度: {len(req.content)}")
    print(f"请求内容: {req}")

    # 检查会话是否存在
    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        print(f"警告: 会话ID {session_id} 不存在")
    else:
        print(f"会话ID {session_id} 有效，标题: {conversation['title']}")

    # 检查模型是否已加载完成
    if not model_status["rag_ready"]:
        return JSONResponse(
            status_code=503,
            content={"error": "中医数据库模型正在加载中", "message": model_status["loading_message"]}
        )

    # 使用路径参数中的会话ID
    req.session_id = session_id

    # 更新用户消息
    conversation_manager.update_conversation_message(req.session_id, req.content, is_user=True)

    # 直接创建Redis历史记录对象
    redis_history = RedisChatMessageHistory(session_id=session_id, url=REDIS_URL)

    # 使用预加载的milvus客户端创建RAG代理
    try:
        agent = RagAgent(redis_url=REDIS_URL, session_id=req.session_id, milvus_client=global_milvus_client)
    except Exception as e:
        error_msg = f"创建RAG代理失败: {str(e)}"
        print(error_msg)
        return JSONResponse(
            status_code=500,
            content={"error": error_msg, "message": "中医数据库模型初始化失败"}
        )

    async def stream_generator():
        """简单的流式响应生成器"""
        full_response = ""
        try:
            # 获取会话的消息历史
            messages = conversation_manager.get_conversation_messages(req.session_id)
            print(f"获取到 {len(messages)} 条历史消息用于RAG")

            # 记录选择的书籍
            if req.books and len(req.books) > 0:
                print(f"用户选择的书籍: {', '.join(req.books)}")
            else:
                print("用户未选择特定书籍，将搜索全部书籍")

            # 构建输入信息
            info = {
                "query": req.content,
                "admin": req.admin,
                "chat_history": messages,
                "books": req.books,
                "top_k": 20,
                "max_iterations": 6,  # ReAct Agent 最大迭代次数（Plan-Execute-Reflect 需要更多轮）
            }

            # 使用 ReAct Agent 处理流式响应
            async for chunk in agent.react_stream(info):
                try:
                    if "partial_result" in chunk:
                        content_value = chunk["partial_result"]
                        if content_value:
                            chunk_str = json.dumps({"content": content_value, "status": "generating"})
                            yield f"data: {chunk_str}\n\n"
                            full_response += content_value
                    elif "thinking_step" in chunk:
                        # 处理思考步骤
                        step_data = json.dumps({"thinking_step": chunk["thinking_step"]})
                        yield f"data: {step_data}\n\n"
                    elif "thinking_update" in chunk:
                        # 处理思考步骤更新
                        update_data = json.dumps({"thinking_update": chunk["thinking_update"]})
                        yield f"data: {update_data}\n\n"
                    elif "thinking_complete" in chunk:
                        # 处理思考完成
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

            # 发送完成标记
            yield f"data: {json.dumps({'content': '', 'status': 'complete'})}\n\n"

            # 更新AI回复信息和Redis历史记录
            conversation_manager.update_conversation_message(req.session_id, full_response, is_user=False)
            redis_history.add_user_message(req.content)
            redis_history.add_ai_message(full_response)

        except Exception as e:
            error_msg = f"RAG流处理异常: {str(e)}"
            print(error_msg)
            error_chunk = json.dumps({"content": f"处理异常: {str(e)}", "status": "error"})
            yield f"data: {error_chunk}\n\n"

    # 创建流式响应
    response = StreamingResponse(stream_generator(), media_type="text/event-stream")
    response.headers["X-Session-ID"] = session_id
    response.headers["Cache-Control"] = "no-cache"
    response.headers["Connection"] = "keep-alive"
    return response





# 新增会话管理接口

@app.post("/conversations", response_model=ConversationResponse)
async def create_conversation(req: ConversationCreateRequest):
    """创建新的会话"""
    print(f"接收到创建会话请求，标题: {req.title}")
    conversation = conversation_manager.create_conversation(req.title)
    print(f"会话创建成功，ID: {conversation['session_id']}")
    # 格式化创建时间为ISO字符串
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
    # 格式化创建时间为ISO字符串
    for conv in conversations:
        conv["created_at"] = datetime.fromtimestamp(conv["created_at"]).isoformat()
    return conversations


@app.get("/conversations/{session_id}", response_model=ConversationResponse)
async def get_conversation(session_id: str):
    """获取指定会话的详情"""
    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")
    # 格式化创建时间为ISO字符串
    conversation["created_at"] = datetime.fromtimestamp(conversation["created_at"]).isoformat()
    return conversation


@app.get("/conversations/{session_id}/messages")
async def get_conversation_messages(session_id: str):
    """获取指定会话的所有消息"""
    # 检查会话是否存在
    conversation = conversation_manager.get_conversation(session_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="会话不存在")

    # 获取会话的所有消息
    messages = conversation_manager.get_conversation_messages(session_id)

    # 如果消息中没有时间戳，添加当前时间作为默认值
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
    # 格式化创建时间为ISO字符串
    conversation["created_at"] = datetime.fromtimestamp(conversation["created_at"]).isoformat()
    return conversation


@app.on_event("startup")
async def startup_event():
    """启动时进行初始化操作"""
    # 在后台线程中预加载模型，避免阻塞应用启动
    threading.Thread(target=preload_milvus, daemon=True).start()
    threading.Thread(target=preload_elasticsearch, daemon=True).start()


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=9978)
