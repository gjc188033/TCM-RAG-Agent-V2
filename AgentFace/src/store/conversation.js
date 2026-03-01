import { ref, reactive, computed } from 'vue'
import { defineStore } from 'pinia'
import chatAPI from '../api'

// 使用Pinia创建会话状态管理
export const useConversationStore = defineStore('conversation', () => {
  // 当前状态
  const currentSessionId = ref(null) // 修正：使用统一的名称currentSessionId
  const isLoading = ref(false)
  const conversations = ref([])
  const messages = ref([])

  // 获取当前会话
  const currentConversation = computed(() => {
    return conversations.value.find(c => c.session_id === currentSessionId.value)
  })

  // 初始化会话数据
  const initializeConversations = async () => {
    try {
      isLoading.value = true
      const response = await chatAPI.getConversations()
      conversations.value = response
      
      // 如果有会话，加载最近一个会话及其历史消息
      if (response.length > 0) {
        await loadConversation(response[0].session_id)
        // 滚动到最新消息 - 这个功能需要在App.vue中实现
      }
    } catch (error) {
      console.error('初始化会话失败:', error)
    } finally {
      isLoading.value = false
    }
  }

  // 创建新会话
  const createNewConversation = async () => {
    try {
      isLoading.value = true
      console.log('开始创建新会话...')
      
      const newConversation = await chatAPI.createConversation()
      console.log('创建会话API返回结果:', newConversation)
      
      // 检查返回的会话数据是否有效
      if (!newConversation || !newConversation.session_id) {
        console.error('创建会话失败: API返回的会话数据无效', newConversation)
        throw new Error('创建会话失败: 服务器返回的会话数据无效')
      }
      
      // 确保会话ID有效
      const sessionId = newConversation.session_id
      if (!sessionId || typeof sessionId !== 'string' || sessionId === 'undefined') {
        console.error('创建会话失败: 无效的会话ID', sessionId)
        throw new Error('创建会话失败: 无效的会话ID')
      }
      
      // 保存会话数据
      conversations.value.unshift(newConversation)
      currentSessionId.value = sessionId
      messages.value = []
      
      console.log(`成功创建新会话，ID: ${sessionId}`)
      return newConversation
    } catch (error) {
      console.error('创建新会话失败:', error)
      throw error // 重新抛出错误，让调用者可以捕获并处理
    } finally {
      isLoading.value = false
    }
  }

  // 加载指定会话
  const loadConversation = async (conversationId, retryCount = 0) => {
    try {
      isLoading.value = true
      // 获取会话详情
      const conversation = await chatAPI.getConversation(conversationId)
      currentSessionId.value = conversationId
      console.log('加载会话成功:', conversation)
      
      // 加载会话的历史消息
      try {
        console.log('正在获取会话历史消息...')
        
        // 使用强制刷新API
        const conversationMessages = retryCount > 0 
          ? await chatAPI.forceRefreshMessages(conversationId)
          : await chatAPI.getConversationMessages(conversationId)
          
        console.log('获取到的历史消息:', conversationMessages)
        
        if (conversationMessages && Array.isArray(conversationMessages)) {
          // 更新消息数组
          messages.value = conversationMessages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp || new Date().toISOString()
          }))
          console.log('处理后的消息列表:', messages.value)
        } else {
          console.warn('获取的历史消息不是数组格式:', conversationMessages)
          
          if (retryCount < 2) {
            // 尝试重试加载
            console.log(`尝试重新加载消息历史(第${retryCount + 1}次)`)
            isLoading.value = false
            return await loadConversation(conversationId, retryCount + 1)
          }
          
          messages.value = []
        }
      } catch (msgError) {
        console.error('加载会话消息失败:', msgError)
        
        if (retryCount < 2) {
          // 尝试重试加载
          console.log(`尝试重新加载消息历史(第${retryCount + 1}次)`)
          isLoading.value = false
          return await loadConversation(conversationId, retryCount + 1)
        }
        
        messages.value = []
      }
    } catch (error) {
      console.error('加载会话失败:', error)
      messages.value = []
    } finally {
      isLoading.value = false
    }
  }

  // 删除会话
  const deleteConversation = async (conversationId) => {
    try {
      await chatAPI.deleteConversation(conversationId)
      conversations.value = conversations.value.filter(c => c.session_id !== conversationId)
      
      // 如果删除的是当前会话，切换到其他会话
      if (currentSessionId.value === conversationId) {
        if (conversations.value.length > 0) {
          await loadConversation(conversations.value[0].session_id)
        } else {
          messages.value = []
          currentSessionId.value = null
        }
      }
    } catch (error) {
      console.error('删除会话失败:', error)
    }
  }

  // 更新会话标题
  const updateConversationTitle = async (conversationId, newTitle) => {
    try {
      const updatedConversation = await chatAPI.updateConversationTitle(conversationId, newTitle)
      
      // 更新本地会话列表中的标题
      const index = conversations.value.findIndex(c => c.session_id === conversationId)
      if (index !== -1) {
        conversations.value[index] = updatedConversation
      }
      
      return updatedConversation
    } catch (error) {
      console.error('更新会话标题失败:', error)
      throw error
    }
  }

  // 发送消息并处理回复（简化版本）
  const sendMessage = async (content, selectedBooks = []) => {
    if (!content.trim()) return

    // 如果没有当前会话，创建一个新会话
    if (!currentSessionId.value) {
      const newConversation = await createNewConversation()
      if (!newConversation) return
    }

    // 创建用户消息
    const userMessage = {
      role: 'user',
      content,
      timestamp: new Date().toISOString()
    }

    // 添加到消息列表
    messages.value.push(userMessage)

    // 创建空的AI消息（用于流式显示）
    const assistantMessage = {
      role: 'assistant',
      content: '',
      timestamp: new Date().toISOString(),
      selectedBooks: selectedBooks || [],
      isThinking: true,
      thinkingSteps: [],
      showThinking: false,
      thinkingExpanded: false,
      currentThinkingStep: ''
    }

    messages.value.push(assistantMessage)
    isLoading.value = true

    try {
      // 使用流式API获取回复
      let accumulatedResponse = ''
      let isGeneratingAnswer = false // 标记是否开始生成实际答案

      // 处理流式响应
      console.log('发送消息，选中的书籍:', selectedBooks);
      const streamController = chatAPI.sendMessageStream(
        content,
        // 处理每个数据块
        (chunk) => {
          if (chunk) {
            console.log('接收到流式数据块:', chunk);

            const lastIndex = messages.value.length - 1;
            if (lastIndex >= 0) {
              // 检查是否是清除进度信息的特殊标记
              if (chunk.includes('🔄 CLEAR_PROGRESS')) {
                // 清除进度信息，准备接收实际答案
                console.log('收到清除进度信息标记，准备接收实际答案');
                isGeneratingAnswer = true;
                accumulatedResponse = '';
                const clearedMessage = {
                  ...messages.value[lastIndex],
                  content: '',
                  isThinking: false
                };
                messages.value.splice(lastIndex, 1, clearedMessage);
                return; // 不显示这个特殊标记
              }

              // 检查是否是进度信息（包含特定的进度标识符）
              const isProgressInfo = chunk.includes('🔍') || chunk.includes('📚') ||
                                    chunk.includes('🧠') || chunk.includes('✨') ||
                                    chunk.includes('正在生成') || chunk.includes('正在检索') ||
                                    chunk.includes('正在使用') || chunk.includes('正在排序');

              if (isProgressInfo && !isGeneratingAnswer) {
                // 如果是进度信息且还没开始生成答案，显示在thinking状态中
                console.log('显示进度信息:', chunk);
                const progressMessage = {
                  ...messages.value[lastIndex],
                  content: chunk,
                  isThinking: true
                };
                messages.value.splice(lastIndex, 1, progressMessage);
              } else if (!isProgressInfo || isGeneratingAnswer) {
                // 如果不是进度信息，或者已经开始生成答案，累积到最终答案中
                if (!isGeneratingAnswer) {
                  isGeneratingAnswer = true;
                  accumulatedResponse = chunk;
                } else {
                  accumulatedResponse += chunk;
                }

                console.log('更新答案内容，当前长度:', accumulatedResponse.length);
                const updatedMessage = {
                  ...messages.value[lastIndex],
                  content: accumulatedResponse,
                  isThinking: false
                };
                messages.value.splice(lastIndex, 1, updatedMessage);
              }
            }
          }
        },
        // 处理错误
        (error) => {
          console.error("Stream error:", error)
          isLoading.value = false

          // 更新消息显示错误
          const lastIndex = messages.value.length - 1;
          if (lastIndex >= 0) {
            const errorMessage = {
              ...messages.value[lastIndex],
              content: accumulatedResponse || `处理出错: ${error.message}`,
              isThinking: false,
              hasError: true
            };
            messages.value.splice(lastIndex, 1, errorMessage);
          }
        },
        // 完成回调
        () => {
          console.log('流式响应完成回调触发');
          isLoading.value = false;

          const lastIndex = messages.value.length - 1;
          if (lastIndex >= 0) {
            const finalMessage = {
              ...messages.value[lastIndex],
              isComplete: true,
              isThinking: false
            };
            messages.value.splice(lastIndex, 1, finalMessage);
          }
        },
        // 会话ID
        currentSessionId.value,
        // 回答模式参数
        'normal',
        // 选中的书籍
        selectedBooks,
        // 思考步骤回调
        (step, isUpdate = false) => {
          console.log('收到思考步骤回调:', step, '是否更新:', isUpdate);
          const lastIndex = messages.value.length - 1;
          if (lastIndex >= 0) {
            const currentMessage = messages.value[lastIndex];

            if (isUpdate) {
              // 更新现有步骤
              const stepIndex = currentMessage.thinkingSteps.findIndex(s => s.title === step.title);
              if (stepIndex >= 0) {
                currentMessage.thinkingSteps[stepIndex] = step;
                console.log('更新思考步骤:', step.title);
              }
            } else {
              // 添加新步骤
              currentMessage.thinkingSteps.push(step);
              console.log('添加新思考步骤:', step.title);
            }

            // 更新当前思考步骤显示
            currentMessage.currentThinkingStep = `${step.icon} ${step.title}`;

            // 触发响应式更新
            const updatedMessage = {
              ...currentMessage,
              thinkingSteps: [...currentMessage.thinkingSteps],
              currentThinkingStep: currentMessage.currentThinkingStep,
              thinkingExpanded: true // 在思考过程中默认展开
            };
            messages.value.splice(lastIndex, 1, updatedMessage);
            console.log('当前思考步骤数量:', updatedMessage.thinkingSteps.length);
          }
        },
        // 思考完成回调
        (thinkingSteps) => {
          console.log('思考完成，收到思考步骤:', thinkingSteps);
          const lastIndex = messages.value.length - 1;
          if (lastIndex >= 0) {
            const finalMessage = {
              ...messages.value[lastIndex],
              thinkingSteps: thinkingSteps || messages.value[lastIndex].thinkingSteps,
              showThinking: true,
              thinkingExpanded: true, // 默认展开，让用户看到思考过程
              isThinking: false,
              currentThinkingStep: ''
            };
            messages.value.splice(lastIndex, 1, finalMessage);
            console.log('更新后的消息:', finalMessage);
          }
        }
      )

      return streamController
    } catch (error) {
      console.error('发送消息失败:', error)
      isLoading.value = false
      throw error
    }
  }

  // 清空当前会话消息
  const clearMessages = () => {
    messages.value = []
  }

  // 直接设置消息列表
  const setMessages = (newMessages) => {
    console.log('直接设置消息列表:', newMessages)
    messages.value = newMessages
  }

  // 添加单条消息
  const addMessage = (message) => {
    messages.value.push(message);
  }

  return {
    currentSessionId,
    isLoading,
    conversations,
    messages,
    currentConversation,
    initializeConversations,
    createNewConversation,
    loadConversation,
    deleteConversation,
    updateConversationTitle,
    sendMessage,
    clearMessages,
    setMessages,
    addMessage
  }
}) 