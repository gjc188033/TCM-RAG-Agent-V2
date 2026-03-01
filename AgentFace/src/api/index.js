import axios from 'axios';

// 创建axios实例
const apiClient = axios.create({
  baseURL: 'http://localhost:9978',  // 使用BaseOne的API端口
  timeout: 30000, // 请求超时时间
  headers: {
    'Content-Type': 'application/json'
  }
});

// 响应拦截器
apiClient.interceptors.response.use(
  response => response.data,
  error => {
    console.error('API请求错误:', error);
    return Promise.reject(error);
  }
);

// 生成随机会话ID
const generateSessionId = () => {
  return 'session_' + Math.random().toString(36).substring(2, 15);
};

// 从localStorage获取会话ID，如果不存在则创建新的
const getSessionId = () => {
  let sessionId = localStorage.getItem('chatSessionId');
  if (!sessionId) {
    sessionId = generateSessionId();
    localStorage.setItem('chatSessionId', sessionId);
  }
  return sessionId;
};

// API功能封装
export const chatAPI = {
  // 获取模型加载状态
  getModelStatus: async () => {
    try {
      const response = await apiClient.get('/model_status');
      return response;
    } catch (error) {
      console.error('获取模型状态失败:', error);
      return {
        rag_ready: false,
        loading_message: '无法连接到服务器'
      };
    }
  },
  
  // 获取数据库统计信息
  getDbStats: async () => {
    try {
      // 使用新的数据库统计信息API
      const response = await apiClient.get('/db_stats');
      
      if (response.status === 'success') {
        return {
          totalDocs: response.total_docs || 0,
          bookCount: response.book_count || 0,
          lastUpdated: response.last_updated || new Date().toISOString()
        };
      } else {
        throw new Error(response.error || '获取数据库统计失败');
      }
    } catch (error) {
      console.error('获取数据库统计信息失败:', error);
      return {
        totalDocs: 0,
        bookCount: 0,
        error: '获取失败'
      };
    }
  },
  
  // 普通模式发送消息到AI
  sendMessage: async (message, sessionId) => {
    try {
      const response = await apiClient.post('/ask', {
        session_id: sessionId,
        admin: 'AI助手',  // 角色定义
        content: message    // 使用content替代topic
      });
      return response;
    } catch (error) {
      console.error('发送消息失败:', error);
      throw error;
    }
  },
  
  // 流式模式发送消息到AI（支持思考过程）
  sendMessageStream: (message, onChunk, onError, onComplete, sessionId, mode = 'normal', selectedBooks = [], onThinkingStep = null, onThinkingComplete = null) => {
    // 始终使用RAG端点
    const endpoint = `/conversations/${sessionId}/messages/ragstream`;

    console.log(`使用RAG回答模式，API端点: ${endpoint}`);
    console.log(`选中的书籍: ${selectedBooks.join(', ') || '无'}`);

    // 使用Fetch API实现流式通信
    const controller = new AbortController();
    
    fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: sessionId,
        admin: 'AI助手',
        content: message,
        books: selectedBooks
      }),
      signal: controller.signal
    })
    .then(response => {
      if (!response.ok) {
        if (response.status === 503) {
          response.json().then(errorData => {
            onError && onError(new Error(errorData.message || '中医数据库模型正在加载中'));
            onComplete && onComplete();
          });
          return Promise.reject('model_loading');
        }
        throw new Error(`HTTP error! Status: ${response.status}`);
      }

      // 设置流式读取器
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      
      // 简单的流式读取函数
      function readStream() {
        reader.read().then(({ done, value }) => {
          if (done) {
            console.log("流式响应完成");
            onComplete && onComplete();
            return;
          }

          const chunk = decoder.decode(value);
          console.log("收到原始数据块:", chunk);

          // 解析SSE格式数据
          const dataChunks = chunk.split('\n\n')
            .filter(line => line.trim().startsWith('data:'))
            .map(line => line.replace(/^data:\s*/, '').trim())
            .filter(line => line);

          console.log("提取的数据块:", dataChunks);

          // 处理所有数据块
          for (const jsonStr of dataChunks) {
            try {
              const jsonData = JSON.parse(jsonStr);
              console.log("解析后的JSON数据:", jsonData);

              // 检查是否为完成标记
              if (jsonData.status === 'complete') {
                console.log("收到流式响应完成标记");
                onComplete && setTimeout(() => onComplete(), 0);
                return;
              }

              // 检查是否为错误
              if (jsonData.status === 'error') {
                console.error("收到错误状态:", jsonData.content);
                onError && onError(new Error(jsonData.content || '处理出错'));
                return;
              }

              // 处理思考步骤
              if (jsonData.thinking_step) {
                console.log("收到思考步骤:", jsonData.thinking_step);
                onThinkingStep && setTimeout(() => onThinkingStep(jsonData.thinking_step), 0);
              }

              // 处理思考步骤更新
              if (jsonData.thinking_update) {
                console.log("收到思考步骤更新:", jsonData.thinking_update);
                onThinkingStep && setTimeout(() => onThinkingStep(jsonData.thinking_update, true), 0);
              }

              // 处理思考完成
              if (jsonData.thinking_complete) {
                console.log("思考过程完成，开始生成答案");
                onThinkingComplete && setTimeout(() => onThinkingComplete(jsonData.thinking_steps || []), 0);
              }

              // 处理正常内容块
              if (jsonData.content !== undefined) {
                console.log("调用onChunk回调，内容:", jsonData.content);
                onChunk && setTimeout(() => onChunk(jsonData.content), 0);
              }
            } catch (e) {
              console.error('解析流数据JSON失败:', e);
              console.error('问题数据:', jsonStr);
            }
          }

          // 继续读取
          readStream();
        }).catch(error => {
          console.error("流式读取错误:", error);
          onError && onError(error);
        });
      }

      // 开始读取
      readStream();

      // 返回控制器，可用于中断请求
      return controller;
    })
    .catch(error => {
      if (error !== 'model_loading') {
        console.error("请求失败:", error);
        onError && onError(error);
      }
    });
    
    // 返回控制器，允许外部中断请求
    return controller;
  },

  // 获取所有会话列表
  getConversations: async (page = 1, pageSize = 20) => {
    try {
      const response = await apiClient.get('/conversations', {
        params: { page, page_size: pageSize }
      });
      return response;
    } catch (error) {
      console.error('获取会话列表失败:', error);
      throw error;
    }
  },

  // 创建新会话
  createConversation: async (title = '新对话') => {
    try {
      const response = await apiClient.post('/conversations', { title });
      return response;
    } catch (error) {
      console.error('创建会话失败:', error);
      throw error;
    }
  },

  // 获取指定会话的详情
  getConversation: async (conversationId) => {
    try {
      const response = await apiClient.get(`/conversations/${conversationId}`);
      return response;
    } catch (error) {
      console.error('获取会话详情失败:', error);
      throw error;
    }
  },

  // 删除会话
  deleteConversation: async (conversationId) => {
    try {
      const response = await apiClient.delete(`/conversations/${conversationId}`);
      return response;
    } catch (error) {
      console.error('删除会话失败:', error);
      throw error;
    }
  },

  // 获取会话的历史消息
  getConversationMessages: async (conversationId) => {
    try {
      const response = await apiClient.get(`/conversations/${conversationId}/messages`);
      return response;
    } catch (error) {
      console.error('获取会话历史消息失败:', error);
      // 返回空数组而不是抛出错误
      return [];
    }
  },

  // 强制刷新会话消息
  forceRefreshMessages: async (conversationId) => {
    try {
      console.log(`强制刷新会话 ${conversationId} 的消息历史`);
      const response = await apiClient.get(`/conversations/${conversationId}/messages`, {
        params: { _timestamp: new Date().getTime() } // 添加时间戳避免缓存
      });
      return response;
    } catch (error) {
      console.error('强制刷新会话消息失败:', error);
      return [];
    }
  },

  // 更新会话标题
  updateConversationTitle: async (conversationId, title) => {
    try {
      const response = await apiClient.put(`/conversations/${conversationId}/title`, { title });
      return response;
    } catch (error) {
      console.error('更新会话标题失败:', error);
      throw error;
    }
  },

  // 获取书籍列表
  getBooks: async (retryCount = 3) => {
    try {
      console.log('尝试获取书籍列表...');
      // 直接使用fetch API，避免axios配置问题
      const response = await fetch('http://localhost:9978/books');
      if (!response.ok) {
        throw new Error(`HTTP error! Status: ${response.status}`);
      }
      
      const books = await response.json();
      
      // 直接处理返回的书籍数组
      if (Array.isArray(books) && books.length > 0) {
        console.log(`成功获取到${books.length}本书籍`);
        return books;
      } else {
        console.warn('获取书籍列表成功，但列表为空');
        return [];
      }
    } catch (error) {
      console.error('获取书籍列表失败:', error);
      
      // 如果还有重试次数，则重试
      if (retryCount > 0) {
        console.log(`将在1秒后重试获取书籍列表，剩余重试次数: ${retryCount}`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        return chatAPI.getBooks(retryCount - 1);
      }
      
      // 不使用默认列表，返回空数组
      return [];
    }
  },
  
  // 获取书名列表
  getBooksName: async (retryCount = 3) => {
    try {
      console.log('尝试获取书名列表...');
      const response = await apiClient.post('/booksname');
      console.log(response);
      if (Array.isArray(response) && response.length > 0) {
        console.log(`成功获取到${response.length}本书的书名`);
        return response;
      } else {
        console.warn('获取书名列表成功，但列表为空');
        return [];
      }
    } catch (error) {
      console.error('获取书名列表失败:', error);
      
      // 如果还有重试次数，则重试
      if (retryCount > 0) {
        console.log(`将在1秒后重试获取书名列表，剩余重试次数: ${retryCount}`);
        await new Promise(resolve => setTimeout(resolve, 1000));
        return chatAPI.getBooksName(retryCount - 1);
      }
      
      return [];
    }
  }
};

export default chatAPI; 