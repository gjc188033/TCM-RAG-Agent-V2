<template>
  <div class="chat-view">
    <!-- 左侧统一侧边栏 -->
    <div class="sidebar" :class="{ collapsed: sidebarCollapsed }">
      <div class="sidebar-header">
        <div class="header-content">
          <!-- 标签页切换按钮 -->
          <div class="tab-buttons" v-if="!sidebarCollapsed">
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'conversations' }"
              @click="activeTab = 'conversations'"
              title="消息记录"
            >
              💬
            </button>
            <button
              class="tab-btn"
              :class="{ active: activeTab === 'books' }"
              @click="activeTab = 'books'"
              title="中医古籍"
            >
              📚
            </button>
          </div>

          <!-- 新建对话按钮 -->
          <button class="new-chat-btn" @click="createNewChat" v-if="!sidebarCollapsed && activeTab === 'conversations'">
            <span>➕</span>
            <span>新建对话</span>
          </button>

          <!-- 折叠按钮 -->
          <button class="collapse-btn" @click="toggleSidebar">
            <span v-if="sidebarCollapsed">☰</span>
            <span v-else>◀</span>
          </button>
        </div>
      </div>

      <div class="sidebar-content" v-if="!sidebarCollapsed">
        <!-- 消息记录标签页 -->
        <div v-if="activeTab === 'conversations'" class="conversation-list">
          <div
            v-for="conversation in conversations"
            :key="conversation.session_id"
            class="conversation-item"
            :class="{ active: conversation.session_id === currentSessionId }"
            @click="loadConversation(conversation.session_id)"
          >
            <div class="conversation-main">
              <div v-if="editingConversationId === conversation.session_id" class="conversation-title-edit">
                <input
                  v-model="editingTitle"
                  @blur="saveTitle(conversation.session_id)"
                  @keydown.enter="saveTitle(conversation.session_id)"
                  @keydown.esc="cancelEdit"
                  class="title-input"
                  ref="titleInput"
                  @click.stop
                />
              </div>
              <div v-else class="conversation-title">{{ conversation.title }}</div>
              <div class="conversation-preview">{{ getLastMessage(conversation.session_id) }}</div>
              <div class="conversation-time">{{ formatTime(conversation.created_at) }}</div>
            </div>
            <div class="conversation-actions" @click.stop>
              <button class="menu-btn" @click="toggleMenu(conversation.session_id)" title="更多操作">
                ⋯
              </button>
              <div
                v-if="activeMenuId === conversation.session_id"
                class="action-menu"
                @click.stop
              >
                <div class="menu-item" @click="editConversationTitle(conversation)">
                  <span class="menu-icon">✏️</span>
                  <span>重命名</span>
                </div>
                <div class="menu-item delete-item" @click="deleteConversation(conversation.session_id)">
                  <span class="menu-icon">🗑️</span>
                  <span>删除</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 书籍选择标签页 -->
        <div v-if="activeTab === 'books'" class="books-content">
          <!-- 书籍选择提示 -->
          <div v-if="showBookAlert" class="book-selection-alert">
            <div class="alert-icon">📚</div>
            <div class="alert-content">
              <div class="alert-title">请选择中医典籍</div>
              <div class="alert-message">至少选择一本古籍进行智能问诊</div>
            </div>
            <button @click="showBookAlert = false" class="alert-close">✕</button>
          </div>
          <!-- 搜索框 -->
          <div class="books-search">
            <div class="search-wrapper">
              <div class="search-icon">🔍</div>
              <input
                v-model="bookSearchQuery"
                type="text"
                placeholder="搜索中医古籍典藏..."
                class="search-input"
              />
              <div v-if="bookSearchQuery" class="clear-search" @click="bookSearchQuery = ''">✕</div>
            </div>
          </div>



          <!-- 书籍列表 -->
          <div class="books-list">
            <div class="books-list-header">
              <div class="header-info">
                <span class="header-icon">📜</span>
                <span class="header-title">中医典藏</span>
                <span class="books-count">{{ filteredBooks.length }}部</span>
              </div>
              <div class="header-actions">
                <span v-if="selectedBooks.length > 0" class="selected-count">已选{{ selectedBooks.length }}部</span>
                <button v-if="selectedBooks.length > 0" @click="clearSelectedBooks" class="clear-all-btn" title="清空所有选择">
                  <span class="clear-icon">🗑️</span>
                </button>
              </div>
            </div>
            <div class="books-scroll">
              <div v-if="filteredBooks.length === 0" class="empty-state">
                <div class="empty-icon">📚</div>
                <div class="empty-text">未找到相关古籍</div>
                <div class="empty-hint">请尝试其他关键词</div>
              </div>
              <div
                v-for="book in filteredBooks"
                :key="book"
                class="book-item"
                :class="{ selected: selectedBooks.includes(book) }"
                @click="toggleBook(book)"
                :title="`点击选择《${book}》`"
              >
                <div class="book-checkbox">
                  <div v-if="selectedBooks.includes(book)" class="checkbox-checked">
                    <span class="check-icon">✓</span>
                  </div>
                  <div v-else class="checkbox-unchecked"></div>
                </div>
                <div class="book-info">
                  <div class="book-icon">📖</div>
                  <div class="book-name">{{ book }}</div>
                </div>
                <div v-if="selectedBooks.includes(book)" class="selected-indicator">
                  <span class="indicator-text">已选</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 主聊天区域 -->
    <div class="main-chat" @click="closeMenu">
      <!-- 消息显示区域 -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="welcome-content">
            <div class="welcome-icon">
              <img src="/icon/img.png" alt="上海市七院中医智能体" class="logo-image" />
            </div>
            <h2>欢迎使用上海市七院中医智能体</h2>
            <p>请描述您的症状或问题，老中医将为您详细解答</p>
          </div>
        </div>
        
        <div v-for="(message, index) in messages" :key="index" class="message-item">
          <div class="message" :class="message.role">
            <div class="message-avatar">
              <div v-if="message.role === 'user'" class="avatar-user">
                <!-- 患者卡通头像 -->
                <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <!-- 脸部 -->
                  <circle cx="32" cy="32" r="28" fill="#FFE4B5"/>
                  <!-- 头发 -->
                  <path d="M32 8C20 8 10 18 10 30C10 25 15 20 22 18C25 16 28 15 32 15C36 15 39 16 42 18C49 20 54 25 54 30C54 18 44 8 32 8Z" fill="#8B4513"/>
                  <!-- 眼睛 -->
                  <circle cx="24" cy="28" r="3" fill="#000"/>
                  <circle cx="40" cy="28" r="3" fill="#000"/>
                  <circle cx="25" cy="27" r="1" fill="#FFF"/>
                  <circle cx="41" cy="27" r="1" fill="#FFF"/>
                  <!-- 鼻子 -->
                  <ellipse cx="32" cy="34" rx="2" ry="3" fill="#FFB6C1"/>
                  <!-- 嘴巴 -->
                  <path d="M28 40C30 42 34 42 36 40" stroke="#000" stroke-width="2" fill="none" stroke-linecap="round"/>
                  <!-- 脸颊红晕 -->
                  <circle cx="18" cy="36" r="4" fill="#FFB6C1" opacity="0.6"/>
                  <circle cx="46" cy="36" r="4" fill="#FFB6C1" opacity="0.6"/>
                </svg>
              </div>
              <div v-else class="avatar-assistant">
                <!-- 传统中医医生卡通头像 -->
                <svg viewBox="0 0 64 64" fill="none" xmlns="http://www.w3.org/2000/svg">
                  <!-- 传统中医帽子背景 -->
                  <ellipse cx="32" cy="18" rx="26" ry="12" fill="#8B0000"/>
                  <!-- 帽子装饰边 -->
                  <ellipse cx="32" cy="18" rx="26" ry="12" stroke="#FFD700" stroke-width="1.5" fill="none"/>
                  <!-- 帽子顶部装饰 -->
                  <circle cx="32" cy="12" r="4" fill="#FFD700"/>
                  <circle cx="32" cy="12" r="2" fill="#FF6B6B"/>
                  <!-- 帽子侧面装饰 -->
                  <circle cx="20" cy="18" r="2" fill="#FFD700"/>
                  <circle cx="44" cy="18" r="2" fill="#FFD700"/>

                  <!-- 脸部 -->
                  <circle cx="32" cy="35" r="22" fill="#FDBCB4"/>

                  <!-- 长胡须 -->
                  <path d="M18 48C20 52 24 55 28 56C30 56.5 32 56.5 32 56.5C32 56.5 34 56.5 36 56C40 55 44 52 46 48C44 50 40 52 36 53C34 53.5 32 53.5 32 53.5C32 53.5 30 53.5 28 53C24 52 20 50 18 48Z" fill="#F5F5F5"/>
                  <!-- 胡须纹理 -->
                  <path d="M22 50C24 52 26 53 28 53.5" stroke="#E8E8E8" stroke-width="0.8"/>
                  <path d="M36 53.5C38 53 40 52 42 50" stroke="#E8E8E8" stroke-width="0.8"/>
                  <path d="M26 51C28 52 30 52.5 32 52.5C34 52.5 36 52 38 51" stroke="#E8E8E8" stroke-width="0.8"/>

                  <!-- 八字胡 -->
                  <path d="M26 42C28 44 30 44.5 32 44.5C34 44.5 36 44 38 42" stroke="#F5F5F5" stroke-width="3" stroke-linecap="round"/>

                  <!-- 眼睛 -->
                  <ellipse cx="26" cy="32" rx="2.5" ry="3" fill="#000"/>
                  <ellipse cx="38" cy="32" rx="2.5" ry="3" fill="#000"/>
                  <circle cx="27" cy="31" r="0.8" fill="#FFF"/>
                  <circle cx="39" cy="31" r="0.8" fill="#FFF"/>

                  <!-- 慈祥的眉毛 -->
                  <path d="M22 28C24 26 28 26 30 28" stroke="#8B4513" stroke-width="2" stroke-linecap="round"/>
                  <path d="M34 28C36 26 40 26 42 28" stroke="#8B4513" stroke-width="2" stroke-linecap="round"/>

                  <!-- 鼻子 -->
                  <ellipse cx="32" cy="37" rx="1.5" ry="2.5" fill="#F4A460"/>

                  <!-- 嘴巴（慈祥微笑） -->
                  <path d="M28 40C30 41.5 34 41.5 36 40" stroke="#8B4513" stroke-width="1.5" fill="none" stroke-linecap="round"/>

                  <!-- 脸部皱纹（显示年长智慧） -->
                  <path d="M20 35C22 36 24 36 26 35" stroke="#E8B4A0" stroke-width="0.8" opacity="0.6"/>
                  <path d="M38 35C40 36 42 36 44 35" stroke="#E8B4A0" stroke-width="0.8" opacity="0.6"/>
                </svg>
              </div>
            </div>
            <div class="message-content">
              <!-- AI消息的思考过程展示 -->
              <div v-if="message.role === 'assistant'">
                <!-- 思考过程展示区域 -->
                <div v-if="message.thinkingSteps && message.thinkingSteps.length > 0" class="thinking-process">
                  <div class="thinking-header" @click="toggleThinking(message)">
                    <span class="thinking-icon">🧠</span>
                    <span class="thinking-title">思考过程</span>
                    <button class="thinking-toggle">
                      {{ message.thinkingExpanded ? '收起' : '展开' }}
                    </button>
                  </div>
                  <div v-if="message.thinkingExpanded" class="thinking-steps">
                    <div v-for="(step, stepIndex) in message.thinkingSteps" :key="stepIndex" class="thinking-step">
                      <div class="step-icon">{{ step.icon }}</div>
                      <div class="step-content">
                        <div class="step-title">{{ step.title }}</div>
                        <div v-if="step.details" class="step-details">{{ step.details }}</div>
                      </div>
                    </div>
                  </div>
                </div>

                <!-- 正在思考的实时显示 -->
                <div v-if="message.isThinking" class="current-thinking">
                  <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                  </div>
                  <div class="thinking-text">
                    <div v-if="message.currentThinkingStep" class="current-step">
                      {{ message.currentThinkingStep }}
                    </div>
                    <div v-else-if="message.selectedBooks && message.selectedBooks.length > 0" class="thinking-with-books">
                      老中医正在根据
                      <span v-for="(book, bookIndex) in message.selectedBooks.slice(0, 3)" :key="book" class="book-name">
                        《{{ book }}》<span v-if="bookIndex < Math.min(message.selectedBooks.length, 3) - 1">、</span>
                      </span>
                      <span v-if="message.selectedBooks.length > 3">等{{ message.selectedBooks.length }}部典籍</span>
                      来分析问题...
                    </div>
                    <div v-else class="default-thinking">
                      老中医正在思考中...
                    </div>
                  </div>
                </div>

                <!-- 最终答案内容 -->
                <div v-if="message.content && !message.isThinking" class="answer-content">
                  <div class="message-text" v-html="formatMessage(message.content)"></div>
                  <div class="message-time">{{ formatTime(message.timestamp) }}</div>
                </div>
              </div>

              <!-- 用户消息 -->
              <div v-else>
                <div class="message-text" v-html="formatMessage(message.content)"></div>
                <div class="message-time">{{ formatTime(message.timestamp) }}</div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- 底部输入框 -->
      <div class="input-container">
        <div class="input-wrapper">
          <textarea
            v-model="inputText"
            ref="textareaRef"
            class="tcm-textarea"
            placeholder="请描述您的症状或问题，老中医将为您详细解答..."
            :disabled="isLoading"
            @keydown="handleKeydown"
            @input="adjustHeight"
            rows="1"
          ></textarea>

          <div class="input-actions">
            <button
              class="send-btn"
              :disabled="!inputText.trim() || isLoading"
              @click="handleSend"
            >
              <span v-if="isLoading" class="loading-icon">⏳</span>
              <span v-else class="send-icon">📤</span>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 成功提示弹窗 -->
    <div v-if="showSuccessToast" class="success-toast">
      <div class="toast-content">
        <div class="toast-icon">✓</div>
        <div class="toast-message">{{ toastMessage }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useConversationStore } from '../../store/conversation'
import { marked } from 'marked'
import chatAPI from '../../api'

// 状态管理
const conversationStore = useConversationStore()

// 基本状态
const isLoading = computed(() => conversationStore.isLoading)
const inputText = ref('')
const textareaRef = ref(null)
const messagesContainer = ref(null)
const sidebarCollapsed = ref(false)
const activeMenuId = ref(null)
const editingConversationId = ref(null)
const editingTitle = ref('')
const showSuccessToast = ref(false)
const toastMessage = ref('')
const showBookAlert = ref(false)

// 侧边栏标签页状态
const activeTab = ref('conversations') // 'conversations' 或 'books'

// 古籍选择相关状态
const availableBooks = ref([])
const selectedBooks = ref([])
const bookSearchQuery = ref('')

// 计算属性
const messages = computed(() => conversationStore.messages)
const conversations = computed(() => conversationStore.conversations)
const currentSessionId = computed(() => conversationStore.currentSessionId)

// 古籍相关计算属性
const filteredBooks = computed(() => {
  if (!bookSearchQuery.value.trim()) {
    return availableBooks.value
  }
  return availableBooks.value.filter(book =>
    book.toLowerCase().includes(bookSearchQuery.value.toLowerCase())
  )
})

// 侧边栏切换
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 古籍选择相关方法
const toggleBook = (bookName) => {
  const index = selectedBooks.value.indexOf(bookName)
  if (index > -1) {
    selectedBooks.value.splice(index, 1)
  } else {
    selectedBooks.value.push(bookName)
  }
}

const clearSelectedBooks = () => {
  selectedBooks.value = []
}

// 显示书籍选择提示
const showBookSelectionAlert = () => {
  showBookAlert.value = true
  // 自动切换到书籍选择标签页
  activeTab.value = 'books'
  // 3秒后自动隐藏提示
  setTimeout(() => {
    showBookAlert.value = false
  }, 3000)
}

// 加载可用书籍列表
const loadAvailableBooks = async () => {
  try {
    console.log('开始加载书籍列表...')
    const books = await chatAPI.getBooksName()

    if (books && books.length > 0) {
      availableBooks.value = books
      console.log(`成功加载书籍列表，共${books.length}本书籍`)

      // 默认选择"本草纲目"
      const benCaoGangMu = books.find(book => book === '本草纲目')
      if (benCaoGangMu && !selectedBooks.value.includes(benCaoGangMu)) {
        selectedBooks.value = [benCaoGangMu]
        console.log('默认选择了《本草纲目》')
      }
    } else {
      console.warn('书籍列表为空')
      availableBooks.value = []
    }
  } catch (error) {
    console.error('获取书籍列表出错:', error)
    availableBooks.value = []
  }
}

// 菜单切换
const toggleMenu = (sessionId) => {
  activeMenuId.value = activeMenuId.value === sessionId ? null : sessionId
}

// 点击其他地方关闭菜单
const closeMenu = () => {
  activeMenuId.value = null
}

// 键盘快捷键
const handleKeydown = (e) => {
  if (e.ctrlKey && e.key === 'Enter') {
    e.preventDefault()
    handleSend()
  }
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// 自动调整输入框高度
const adjustHeight = () => {
  if (!textareaRef.value) return
  textareaRef.value.style.height = 'auto'
  textareaRef.value.style.height = `${Math.min(textareaRef.value.scrollHeight, 120)}px`
}

// 发送消息
const handleSend = async () => {
  if (!inputText.value.trim() || isLoading.value) return

  // 检查是否选择了书籍
  if (!selectedBooks.value || selectedBooks.value.length === 0) {
    showBookSelectionAlert()
    return
  }

  try {
    const message = inputText.value.trim()
    inputText.value = ''

    if (textareaRef.value) {
      textareaRef.value.style.height = 'auto'
    }

    console.log('ChatView发送消息，选中的书籍:', selectedBooks.value)
    await conversationStore.sendMessage(message, selectedBooks.value)

    await nextTick()
    scrollToBottom()

  } catch (error) {
    console.error('发送消息失败:', error)
  }
}



// 创建新对话
const createNewChat = async () => {
  try {
    await conversationStore.createNewConversation()
  } catch (error) {
    console.error('创建新对话失败:', error)
  }
}

// 加载对话
const loadConversation = async (sessionId) => {
  try {
    await conversationStore.loadConversation(sessionId)
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('加载对话失败:', error)
  }
}

// 滚动到底部
const scrollToBottom = () => {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

// 切换思考过程的展开/收起
const toggleThinking = (message) => {
  message.thinkingExpanded = !message.thinkingExpanded
}

// 获取对话的最后一条消息预览
const getLastMessage = (sessionId) => {
  if (sessionId === currentSessionId.value && messages.value.length > 0) {
    const lastMessage = messages.value[messages.value.length - 1]
    const content = lastMessage.content || ''
    return content.length > 30 ? content.substring(0, 30) + '...' : content
  }
  return '暂无消息'
}

// 编辑对话标题
const editConversationTitle = (conversation) => {
  activeMenuId.value = null // 关闭菜单
  editingConversationId.value = conversation.session_id
  editingTitle.value = conversation.title

  // 下一帧聚焦输入框
  nextTick(() => {
    const titleInput = document.querySelector('.title-input')
    if (titleInput) {
      titleInput.focus()
      titleInput.select()
    }
  })
}

// 保存标题
const saveTitle = async (sessionId) => {
  if (editingTitle.value.trim() && editingTitle.value.trim() !== '') {
    try {
      await conversationStore.updateConversationTitle(sessionId, editingTitle.value.trim())
      showToast('标题更新成功')
      console.log('标题更新成功:', sessionId, editingTitle.value.trim())
    } catch (error) {
      console.error('更新标题失败:', error)
      showToast('更新失败，请重试')
    }
  }
  cancelEdit()
}

// 取消编辑
const cancelEdit = () => {
  editingConversationId.value = null
  editingTitle.value = ''
}

// 显示成功提示
const showToast = (message) => {
  toastMessage.value = message
  showSuccessToast.value = true

  // 3秒后开始淡出动画
  setTimeout(() => {
    const toast = document.querySelector('.success-toast')
    if (toast) {
      toast.style.animation = 'slideOutRight 0.3s ease-in forwards'
      setTimeout(() => {
        showSuccessToast.value = false
      }, 300)
    }
  }, 3000)
}

// 删除对话
const deleteConversation = async (sessionId) => {
  activeMenuId.value = null // 关闭菜单
  try {
    await conversationStore.deleteConversation(sessionId)
    showToast('对话删除成功')
    console.log('对话删除成功:', sessionId)
  } catch (error) {
    console.error('删除对话失败:', error)
    showToast('删除失败，请重试')
  }
}

// 格式化消息内容
const formatMessage = (content) => {
  if (!content) return ''
  return marked(content)
}

// 格式化时间
const formatTime = (timestamp) => {
  if (!timestamp) return ''
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  
  return date.toLocaleDateString()
}

// 初始化
onMounted(async () => {
  try {
    // 并行加载对话和书籍列表
    await Promise.all([
      conversationStore.initializeConversations(),
      loadAvailableBooks()
    ])
    await nextTick()
    scrollToBottom()
  } catch (error) {
    console.error('初始化失败:', error)
  }
})
</script>

<style scoped>
.chat-view {
  height: 100%;
  display: flex;
  background: #ffffff;
  color: #000000;
}

/* 左侧边栏 */
.sidebar {
  width: 240px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.sidebar.collapsed {
  width: 45px;
}

.sidebar-header {
  padding: 10px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}

/* 标签页按钮 */
.tab-buttons {
  display: flex;
  gap: 6px;
  background: rgba(0, 0, 0, 0.05);
  padding: 4px;
  border-radius: 8px;
}

.tab-btn {
  background: none;
  border: none;
  font-size: 18px;
  cursor: pointer;
  padding: 8px 12px;
  border-radius: 6px;
  transition: all 0.3s ease;
  opacity: 0.6;
  position: relative;
  overflow: hidden;
}

.tab-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.8);
  opacity: 0.8;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.tab-btn:hover::before {
  opacity: 1;
}

.tab-btn.active {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  opacity: 1;
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.3);
  color: white;
}

.tab-btn.active::before {
  opacity: 0;
}

.collapse-btn {
  background: none;
  border: none;
  font-size: 14px;
  cursor: pointer;
  padding: 6px;
  border-radius: 4px;
  color: #666666;
  min-width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-btn:hover {
  background: #f3f4f6;
  color: #000000;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.conversation-item {
  padding: 8px 10px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
  position: relative;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.conversation-item:hover {
  background: #f8f9fa;
}

.conversation-item:hover .conversation-actions {
  opacity: 1;
}

.conversation-item.active {
  background: #e8f5e8;
  border-left: 3px solid #10b981;
}

.conversation-main {
  flex: 1;
  min-width: 0;
}

.conversation-title {
  font-weight: 500;
  color: #000000;
  margin-bottom: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  line-height: 1.2;
}

.conversation-preview {
  font-size: 10px;
  color: #888888;
  margin-bottom: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.2;
}

.conversation-time {
  font-size: 9px;
  color: #999999;
}

.conversation-title-edit {
  margin-bottom: 3px;
}

.title-input {
  width: 100%;
  border: 1px solid #4a90e2;
  border-radius: 4px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 500;
  color: #000000;
  background: #ffffff;
  outline: none;
  line-height: 1.2;
}

.conversation-actions {
  position: relative;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.menu-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 4px;
  font-size: 14px;
  color: #666666;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s ease;
  font-weight: bold;
}

.menu-btn:hover {
  background: #f0f0f0;
  color: #333333;
}

.action-menu {
  position: absolute;
  top: 100%;
  right: 0;
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 100px;
  overflow: hidden;
  margin-top: 4px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.2s ease;
  font-size: 12px;
  color: #333333;
  white-space: nowrap;
}

.menu-item:hover {
  background: #f8f9fa;
}

.menu-item.delete-item {
  color: #dc3545;
}

.menu-item.delete-item:hover {
  background: #fff5f5;
  color: #dc3545;
}

.menu-icon {
  font-size: 12px;
  width: 16px;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 成功提示弹窗 */
.success-toast {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 9999;
  animation: slideInRight 0.3s ease-out;
}

.toast-content {
  background: #ffffff;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 200px;
}

.toast-icon {
  width: 20px;
  height: 20px;
  background: #10b981;
  color: #ffffff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
  flex-shrink: 0;
}

.toast-message {
  color: #333333;
  font-size: 13px;
  font-weight: 500;
}

@keyframes slideInRight {
  from {
    transform: translateX(100%);
    opacity: 0;
  }
  to {
    transform: translateX(0);
    opacity: 1;
  }
}

@keyframes slideOutRight {
  from {
    transform: translateX(0);
    opacity: 1;
  }
  to {
    transform: translateX(100%);
    opacity: 0;
  }
}

/* 书籍选择相关样式 */
.books-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 书籍选择提示框 */
.book-selection-alert {
  margin: 12px;
  padding: 16px;
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 2px solid #f59e0b;
  border-radius: 12px;
  display: flex;
  align-items: center;
  gap: 12px;
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.2);
  animation: slideInDown 0.3s ease-out;
}

.alert-icon {
  font-size: 24px;
  flex-shrink: 0;
}

.alert-content {
  flex: 1;
}

.alert-title {
  font-size: 14px;
  font-weight: 600;
  color: #92400e;
  margin-bottom: 2px;
}

.alert-message {
  font-size: 12px;
  color: #b45309;
  line-height: 1.4;
}

.alert-close {
  background: none;
  border: none;
  color: #92400e;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  padding: 4px;
  border-radius: 4px;
  transition: all 0.2s;
  flex-shrink: 0;
}

.alert-close:hover {
  background: rgba(146, 64, 14, 0.1);
  transform: scale(1.1);
}

@keyframes slideInDown {
  from {
    transform: translateY(-20px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.books-search {
  padding: 16px 12px;
  border-bottom: 1px solid #e5e7eb;
  background: linear-gradient(135deg, #f8fffe 0%, #f0fdf4 100%);
}

.search-wrapper {
  position: relative;
  display: flex;
  align-items: center;
  background: #ffffff;
  border: 2px solid #e5e7eb;
  border-radius: 12px;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.search-wrapper:focus-within {
  border-color: #10b981;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
  transform: translateY(-1px);
}

.search-icon {
  padding: 0 12px;
  color: #9ca3af;
  font-size: 14px;
}

.search-input {
  flex: 1;
  padding: 12px 8px;
  border: none;
  outline: none;
  font-size: 13px;
  background: transparent;
  color: #374151;
}

.search-input::placeholder {
  color: #9ca3af;
  font-style: italic;
}

.clear-search {
  padding: 8px 12px;
  color: #9ca3af;
  cursor: pointer;
  font-size: 12px;
  transition: color 0.2s;
}

.clear-search:hover {
  color: #dc2626;
}



.books-list {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  margin: 0 8px 8px 8px;
  background: #ffffff;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.books-list-header {
  padding: 12px 16px;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-bottom: 1px solid #e2e8f0;
  border-radius: 8px 8px 0 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  font-size: 16px;
  color: #64748b;
}

.header-title {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.books-count {
  background: linear-gradient(135deg, #e2e8f0 0%, #cbd5e1 100%);
  color: #475569;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.selected-count {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 4px 8px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}

.clear-all-btn {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.2);
  color: #dc2626;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: 6px;
  transition: all 0.2s;
  display: flex;
  align-items: center;
}

.clear-all-btn:hover {
  background: rgba(220, 38, 38, 0.8);
  border-color: rgba(220, 38, 38, 0.8);
  color: white;
  transform: scale(1.05);
}

.clear-icon {
  font-size: 12px;
}

.books-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

/* 空状态样式 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 12px;
  opacity: 0.5;
}

.empty-text {
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
  margin-bottom: 4px;
}

.empty-hint {
  font-size: 12px;
  color: #9ca3af;
}

/* 书籍项目样式 */
.book-item {
  display: flex;
  align-items: center;
  padding: 12px;
  margin-bottom: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  border-radius: 8px;
  border: 1px solid transparent;
  position: relative;
}

.book-item:hover {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border-color: #e2e8f0;
  transform: translateX(4px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.book-item.selected {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  border-color: #10b981;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.book-checkbox {
  margin-right: 12px;
  position: relative;
}

.checkbox-checked {
  width: 20px;
  height: 20px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}

.check-icon {
  color: white;
  font-size: 12px;
  font-weight: bold;
}

.checkbox-unchecked {
  width: 20px;
  height: 20px;
  border: 2px solid #d1d5db;
  border-radius: 4px;
  transition: all 0.2s;
}

.book-item:hover .checkbox-unchecked {
  border-color: #10b981;
  background: rgba(16, 185, 129, 0.05);
}

.book-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.book-icon {
  font-size: 16px;
  color: #64748b;
}

.book-item.selected .book-icon {
  color: #10b981;
}

.book-name {
  font-size: 13px;
  color: #374151;
  flex: 1;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
  font-weight: 500;
}

.book-item.selected .book-name {
  color: #166534;
  font-weight: 600;
}

.selected-indicator {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 600;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}

.indicator-text {
  display: block;
}

/* 滚动条美化 */
.books-scroll::-webkit-scrollbar,
.selected-list::-webkit-scrollbar {
  width: 6px;
}

.books-scroll::-webkit-scrollbar-track,
.selected-list::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 3px;
}

.books-scroll::-webkit-scrollbar-thumb,
.selected-list::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #cbd5e1 0%, #94a3b8 100%);
  border-radius: 3px;
  transition: background 0.2s;
}

.books-scroll::-webkit-scrollbar-thumb:hover,
.selected-list::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
}

/* 书籍内容区域整体美化 */
.books-content {
  background: linear-gradient(135deg, #f8fffe 0%, #f0fdf4 100%);
  position: relative;
}

.books-content::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, #10b981 0%, #059669 50%, #10b981 100%);
  background-size: 200% 100%;
  animation: shimmer 3s ease-in-out infinite;
}

@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}

.new-chat-btn {
  flex: 1;
  padding: 5px 8px;
  background: #10b981;
  color: #ffffff;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 3px;
  font-weight: 500;
  font-size: 11px;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  background: #059669;
}

/* 主聊天区域 */
.main-chat {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px;
  background: #f8fafc;
  background-image:
    radial-gradient(circle at 25% 25%, rgba(16, 185, 129, 0.02) 0%, transparent 50%),
    radial-gradient(circle at 75% 75%, rgba(59, 130, 246, 0.02) 0%, transparent 50%);
  display: flex;
  flex-direction: column;
}

.welcome-message {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  color: #1f2937;
  position: relative;
  overflow: hidden;
}

.welcome-message::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(16, 185, 129, 0.05) 0%, transparent 70%);
  border-radius: 50%;
  transform: translate(-50%, -50%);
  animation: gentleRotate 20s linear infinite;
  z-index: 0;
}

.welcome-content {
  position: relative;
  z-index: 1;
  text-align: center;
  max-width: 600px;
  width: 100%;
  animation: fadeInUp 0.8s ease-out;
}

.welcome-icon {
  margin-bottom: 32px;
  display: flex;
  justify-content: center;
  align-items: center;
}

.logo-image {
  width: 180px;
  height: 180px;
  object-fit: contain;
  border-radius: 0;
  border: none;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
  transition: transform 0.3s ease, box-shadow 0.3s ease;
  animation: gentlePulse 3s ease-in-out infinite;
}

.logo-image:hover {
  transform: scale(1.05);
  box-shadow: 0 16px 40px rgba(0, 0, 0, 0.2);
  animation-play-state: paused;
}

.welcome-content h2 {
  color: #1f2937;
  margin-bottom: 16px;
  font-size: 32px;
  font-weight: 600;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.2;
}

.welcome-content p {
  color: #6b7280;
  font-size: 18px;
  line-height: 1.6;
  margin: 0;
  font-weight: 400;
}

.message-item {
  margin-bottom: 20px;
}

.message {
  display: flex;
  gap: 12px;
  margin-bottom: 4px;
  align-items: flex-start;
}

.message.user {
  margin-left: auto;
  flex-direction: row-reverse;
}

.message.assistant {
  margin-right: 0;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 2px;
  box-shadow: 0 3px 12px rgba(0, 0, 0, 0.15);
  transition: all 0.2s ease;
}

.avatar-user {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(135deg, #87CEEB 0%, #4682B4 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 2px solid #fff;
}

.avatar-user svg {
  width: 36px;
  height: 36px;
}

.avatar-assistant {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  background: linear-gradient(135deg, #98FB98 0%, #228B22 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 2px solid #fff;
  position: relative;
}

.avatar-assistant svg {
  width: 36px;
  height: 36px;
}

.avatar-assistant::before {
  content: '';
  position: absolute;
  inset: -3px;
  border-radius: 50%;
  background: linear-gradient(135deg, #98FB98, #32CD32, #228B22);
  z-index: -1;
  opacity: 0.4;
}

.message-content {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 16px;
  padding: 12px 16px;
  position: relative;
  max-width: 70%;
  width: fit-content;
  min-width: 80px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  transition: all 0.2s ease;
}

.message.user .message-content {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
  max-width: 70%;
  border-radius: 16px 16px 4px 16px;
}

.message.user .message-content .message-text {
  color: white;
}

.message.user .message-content .message-time {
  color: rgba(255, 255, 255, 0.8);
}

.message.assistant .message-content {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  max-width: 80%;
  border-radius: 16px 16px 16px 4px;
}

.message-content:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.message-text {
  color: #1f2937;
  line-height: 1.6;
  margin-bottom: 6px;
  font-size: 16px;
  text-align: left;
  word-wrap: break-word;
  word-break: break-word;
}

.message-text p {
  margin: 0 0 8px 0;
}

.message-text p:last-child {
  margin-bottom: 0;
}

.message-text pre {
  background: #f3f4f6;
  border-radius: 8px;
  padding: 12px;
  margin: 8px 0;
  overflow-x: auto;
  font-size: 14px;
}

.message.user .message-text pre {
  background: rgba(255, 255, 255, 0.2);
}

.message-text code {
  background: #f3f4f6;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 14px;
}

.message.user .message-text code {
  background: rgba(255, 255, 255, 0.2);
}

.message-time {
  font-size: 12px;
  color: #6b7280;
  text-align: left;
  margin-top: 4px;
}

.message.assistant .message-time {
  text-align: left;
}

/* 输入框区域 */
.input-container {
  padding: 16px 20px 20px;
  border-top: 1px solid #e5e7eb;
  background: #ffffff;
  background-image: linear-gradient(to top, #ffffff 0%, #f8fafc 100%);
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #ffffff;
  border: 2px solid #e5e7eb;
  border-radius: 20px;
  padding: 12px 16px;
  transition: all 0.3s ease;
  max-width: 100%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.input-wrapper:focus-within {
  border-color: #10b981;
  box-shadow: 0 0 0 3px rgba(16, 185, 129, 0.1), 0 4px 12px rgba(0, 0, 0, 0.1);
}

.tcm-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 16px;
  line-height: 1.5;
  color: #1f2937;
  background: transparent;
  min-height: 24px;
  max-height: 120px;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.tcm-textarea::placeholder {
  color: #9ca3af;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.send-btn {
  padding: 8px;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #ffffff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.3);
}

.send-btn:hover:not(:disabled) {
  background: linear-gradient(135deg, #059669 0%, #047857 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(16, 185, 129, 0.4);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 2px 4px rgba(16, 185, 129, 0.2);
}

/* 取消按钮样式 */
.cancel-btn {
  padding: 8px;
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: #ffffff;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 36px;
  height: 36px;
  font-size: 14px;
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
  margin-right: 8px;
}

.cancel-btn:hover {
  background: linear-gradient(135deg, #dc2626 0%, #b91c1c 100%);
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(239, 68, 68, 0.4);
}

.cancel-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 4px rgba(239, 68, 68, 0.3);
}

.cancel-icon {
  font-size: 16px;
}

/* 加载动画 */
.loading-container {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 0;
}

.typing-indicator {
  display: flex;
  gap: 8px;
  align-items: center;
  justify-content: flex-start;
}

.loading-text {
  color: #6b7280;
  font-size: 14px;
  font-style: italic;
  animation: fadeInOut 2s infinite ease-in-out;
}

/* 带书籍的思考状态 */
.thinking-with-books {
  line-height: 1.5;
}

.thinking-with-books .book-name {
  color: #059669;
  font-weight: 500;
  font-style: normal;
}

.default-thinking {
  color: #6b7280;
}

/* 参考书籍显示样式 */
.reference-books {
  display: flex;
  flex-direction: column;
  gap: 4px;
  line-height: 1.4;
}

.reference-label {
  color: #10b981;
  font-weight: 600;
  font-size: 13px;
}

.book-list {
  color: #374151;
  font-size: 13px;
  font-weight: 500;
}

.book-item {
  color: #059669;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.1) 100%);
  padding: 1px 4px;
  border-radius: 3px;
  margin: 0 1px;
}

.more-books {
  color: #6b7280;
  font-size: 12px;
  font-style: italic;
}

.thinking-suffix {
  color: #6b7280;
  font-size: 13px;
  margin-top: 2px;
}

/* 思考过程样式 */
.thinking-process {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(5, 150, 105, 0.05) 100%);
  border: 1px solid rgba(16, 185, 129, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  transition: all 0.3s ease;
}

.thinking-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
  cursor: pointer;
}

.thinking-icon {
  font-size: 18px;
}

.thinking-title {
  font-weight: 600;
  color: #059669;
  font-size: 14px;
}

.thinking-toggle {
  margin-left: auto;
  background: rgba(16, 185, 129, 0.1);
  border: 1px solid rgba(16, 185, 129, 0.3);
  color: #059669;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.thinking-toggle:hover {
  background: rgba(16, 185, 129, 0.2);
}

.thinking-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.thinking-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.7);
  border-radius: 8px;
  border-left: 3px solid #10b981;
}

.step-icon {
  font-size: 16px;
  margin-top: 2px;
}

.step-content {
  flex: 1;
}

.step-title {
  font-weight: 500;
  color: #374151;
  font-size: 14px;
  margin-bottom: 4px;
}

.step-details {
  color: #6b7280;
  font-size: 13px;
  line-height: 1.4;
}

/* 当前思考状态 */
.current-thinking {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(16, 185, 129, 0.05);
  border-radius: 8px;
  margin-bottom: 16px;
}

.thinking-text {
  color: #6b7280;
  font-size: 14px;
  font-style: italic;
}

.current-step {
  color: #059669;
  font-weight: 500;
}

/* 答案内容 */
.answer-content {
  background: white;
  border-radius: 8px;
  padding: 16px;
}

.default-thinking {
  color: #6b7280;
  font-size: 14px;
}

.typing-indicator span {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  animation: typing 1.6s infinite ease-in-out;
  box-shadow: 0 2px 6px rgba(16, 185, 129, 0.4);
  position: relative;
}

.typing-indicator span::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: 50%;
  background: linear-gradient(135deg, #10b981, #059669);
  opacity: 0.3;
  z-index: -1;
  animation: pulse 1.6s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(1)::before {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
}

.typing-indicator span:nth-child(2)::before {
  animation-delay: -0.16s;
}

.typing-indicator span:nth-child(3)::before {
  animation-delay: 0s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.7);
    opacity: 0.5;
  }
  40% {
    transform: scale(1.2);
    opacity: 1;
  }
}

@keyframes pulse {
  0%, 80%, 100% {
    transform: scale(1);
    opacity: 0.2;
  }
  40% {
    transform: scale(1.5);
    opacity: 0.4;
  }
}

@keyframes fadeInOut {
  0%, 100% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
  }
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes gentlePulse {
  0%, 100% {
    transform: scale(1);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.15);
  }
  50% {
    transform: scale(1.02);
    box-shadow: 0 16px 40px rgba(16, 185, 129, 0.2);
  }
}

@keyframes gentleRotate {
  from {
    transform: translate(-50%, -50%) rotate(0deg);
  }
  to {
    transform: translate(-50%, -50%) rotate(360deg);
  }
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 220px;
  }

  .sidebar.collapsed {
    width: 40px;
  }

  .message {
    max-width: 90%;
  }

  .conversation-item {
    padding: 6px 8px;
  }

  .conversation-title {
    font-size: 11px;
  }

  .conversation-preview {
    font-size: 9px;
  }

  .welcome-content h2 {
    font-size: 28px;
  }

  .welcome-content p {
    font-size: 16px;
  }

  .logo-image {
    width: 150px;
    height: 150px;
  }
}

@media (max-width: 480px) {
  .welcome-content h2 {
    font-size: 24px;
  }

  .welcome-content p {
    font-size: 14px;
    padding: 0 10px;
  }

  .logo-image {
    width: 120px;
    height: 120px;
  }

  .welcome-message {
    padding: 20px 15px;
  }
}
</style>

<style scoped>
.chat-view {
  height: 100%;
  display: flex;
  background: #ffffff;
  color: #000000;
}

/* 左侧边栏 */
.sidebar {
  width: 280px;
  background: #ffffff;
  border-right: 1px solid #e5e7eb;
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.sidebar.collapsed {
  width: 50px;
}

.sidebar-header {
  padding: 15px;
  border-bottom: 1px solid #e5e7eb;
  background: #ffffff;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.collapse-btn {
  background: none;
  border: none;
  font-size: 16px;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  color: #666666;
  min-width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.collapse-btn:hover {
  background: #f3f4f6;
  color: #000000;
}

.sidebar-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #ffffff;
}

.conversation-list {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}

.conversation-item {
  padding: 16px;
  border-bottom: 1px solid #f0f0f0;
  cursor: pointer;
  transition: all 0.2s ease;
  background: #ffffff;
  position: relative;
}

.conversation-item:hover {
  background: #f8f9fa;
}

.conversation-item.active {
  background: #e8f5e8;
  border-left: 3px solid #10b981;
}

.conversation-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #10b981;
}

.conversation-title {
  font-weight: 500;
  color: #000000;
  margin-bottom: 6px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 14px;
}

.conversation-preview {
  font-size: 12px;
  color: #888888;
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
}

.conversation-time {
  font-size: 11px;
  color: #999999;
}

.new-chat-btn {
  flex: 1;
  padding: 8px 12px;
  background: #10b981;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-weight: 500;
  font-size: 13px;
  transition: all 0.2s ease;
}

.new-chat-btn:hover {
  background: #059669;
}


</style>
