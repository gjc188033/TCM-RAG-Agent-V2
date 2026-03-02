<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import chatAPI from './api/index.js'
import { marked } from 'marked'
import { useConversationStore } from './store/conversation'

// 导入组件
import ChatView from './components/Views/ChatView.vue'

// 应用状态管理
const conversationStore = useConversationStore()

// 应用状态
const currentView = ref('chat') // 当前视图：chat, records, books, login
const modelStatus = ref({
  rag_ready: false,
  loading_message: "正在初始化船代知识库..."
})

// 配置marked
marked.setOptions({
  highlight: function (code, lang) {
    return code
  },
  langPrefix: 'hljs language-'
})

// 视图切换处理
const handleViewChange = (view) => {
  currentView.value = view
  console.log('切换到视图:', view)
}

// 登录处理
const handleLogin = () => {
  ElMessage.info('登录功能开发中...')
}

// 轮询获取模型状态
const startModelStatusPolling = async () => {
  try {
    const checkModelStatus = async () => {
      try {
        const status = await chatAPI.getModelStatus()
        modelStatus.value = status
      } catch (error) {
        console.error('获取模型状态失败:', error)
      }
    }

    await checkModelStatus()

    setInterval(checkModelStatus, 10000)
  } catch (error) {
    console.error('启动模型状态轮询失败:', error)
  }
}

// 初始化应用
onMounted(async () => {
  try {
    console.log('初始化船代智能问答助手...')

    await startModelStatusPolling()

    console.log('应用初始化完成')
  } catch (error) {
    console.error('应用初始化失败:', error)
    ElMessage.error('应用初始化失败，请刷新页面重试')
  }
})
</script>


<template>
  <div class="ship-app">
    <!-- 顶部导航栏 -->
    <header class="ship-header">
      <div class="header-left">
        <div class="logo-section">
          <div class="logo-circle">
            <span class="logo-icon">🚢</span>
          </div>
          <div class="logo-text">
            <h1>船代智能问答助手</h1>
            <p>专业船务咨询，智能操作指引</p>
          </div>
        </div>
      </div>

      <div class="header-center">
        <div class="clinic-status">
          <div v-if="!modelStatus.rag_ready" class="status-loading">
            <span class="status-icon">⏳</span>
            <span>{{ modelStatus.loading_message }}</span>
          </div>
          <div v-else class="status-ready">
            <span class="status-icon">✅</span>
            <span>助手就绪</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <nav class="nav-menu">
          <button class="nav-item" :class="{ active: currentView === 'chat' }" @click="handleViewChange('chat')">
            <span class="nav-icon">💬</span>
            <span>问答</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'records' }" @click="handleViewChange('records')">
            <span class="nav-icon">📋</span>
            <span>历史</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'books' }" @click="handleViewChange('books')">
            <span class="nav-icon">📚</span>
            <span>知识库</span>
          </button>
          <button class="nav-item" @click="handleLogin">
            <span class="nav-icon">👤</span>
            <span>登录</span>
          </button>
        </nav>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="ship-main">
      <!-- 聊天视图 -->
      <div v-if="currentView === 'chat'" class="view-container">
        <ChatView />
      </div>

      <!-- 其他视图占位符 -->
      <div v-else class="view-container">
        <div class="coming-soon">
          <div class="coming-icon">🚧</div>
          <h2>功能开发中</h2>
          <p>{{ currentView === 'records' ? '历史记录管理' : currentView === 'books' ? '知识库管理' : '用户登录' }}功能正在开发中，敬请期待...</p>
        </div>
      </div>
    </main>
  </div>
</template>



<style>
/* 全局样式重置 */
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', sans-serif;
  background: linear-gradient(135deg, #f0f4f8 0%, #d5e3f0 100%);
}

#app {
  width: 100%;
  height: 100vh;
  margin: 0;
  padding: 0;
}

* {
  box-sizing: border-box;
}

/* 航运深蓝主题色彩 */
:root {
  --ship-primary: #1e3a5f;       /* 深靛蓝 - 主色调 */
  --ship-secondary: #2563eb;     /* 亮蓝 - 辅助色 */
  --ship-accent: #0ea5e9;        /* 天蓝 - 强调色 */
  --ship-light: #f0f7ff;         /* 浅蓝 - 浅色背景 */
  --ship-dark: #0f172a;          /* 深海蓝 - 深色文字 */
  --ship-success: #10b981;       /* 绿色 - 成功状态 */
  --ship-danger: #ef4444;        /* 红色 - 错误状态 */
  --ship-warning: #f59e0b;       /* 琥珀色 - 警告 */
  --ship-shadow: rgba(30, 58, 95, 0.2);
}
</style>

<style scoped>
/* 应用主容器 */
.ship-app {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f0f4f8 0%, #d5e3f0 100%);
  font-family: 'Microsoft YaHei', '微软雅黑', 'Segoe UI', sans-serif;
}

/* 顶部导航栏 */
.ship-header {
  height: 60px;
  background: linear-gradient(90deg, var(--ship-primary) 0%, #1e40af 50%, var(--ship-secondary) 100%);
  box-shadow: 0 4px 12px var(--ship-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: relative;
  z-index: 100;
}

.ship-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><path d="M0,10 Q25,0 50,10 T100,10 L100,20 L0,20 Z" fill="rgba(255,255,255,0.08)"/></svg>') repeat-x;
  background-size: 200px 20px;
  pointer-events: none;
}

.header-left {
  flex: 1;
}

.logo-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.logo-circle {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(255,255,255,0.2), rgba(255,255,255,0.05));
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.logo-icon {
  font-size: 22px;
}

.logo-text h1 {
  color: var(--ship-light);
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
  letter-spacing: 1.5px;
}

.logo-text p {
  color: rgba(224, 242, 254, 0.8);
  font-size: 10px;
  margin: 1px 0 0 0;
  font-style: italic;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.clinic-status {
  background: rgba(255, 255, 255, 0.12);
  padding: 6px 15px;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
}

.status-loading, .status-ready {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ship-light);
  font-size: 12px;
  font-weight: 500;
}

.status-icon {
  font-size: 14px;
}

.header-right {
  flex: 1;
  display: flex;
  justify-content: flex-end;
}

.nav-menu {
  display: flex;
  gap: 4px;
}

.nav-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 6px 12px;
  background: transparent;
  border: none;
  color: rgba(224, 242, 254, 0.8);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s ease;
  font-size: 10px;
  min-width: 50px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.12);
  color: var(--ship-light);
  transform: translateY(-2px);
}

.nav-item.active {
  background: rgba(14, 165, 233, 0.3);
  color: #e0f2fe;
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
}

.nav-icon {
  font-size: 14px;
}

/* 主内容区域 */
.ship-main {
  flex: 1;
  overflow: hidden;
  position: relative;
}

/* 视图容器 */
.view-container {
  width: 100%;
  height: 100%;
}

/* 开发中页面 */
.coming-soon {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.9);
  color: var(--ship-dark);
}

.coming-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.coming-soon h2 {
  color: var(--ship-primary);
  font-size: 28px;
  margin-bottom: 15px;
}

.coming-soon p {
  color: #666;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .ship-header {
    height: 50px;
    padding: 0 15px;
  }

  .logo-text h1 {
    font-size: 16px;
  }

  .logo-text p {
    display: none;
  }

  .nav-item {
    padding: 6px 10px;
    min-width: 45px;
    font-size: 10px;
  }
}

@media (max-width: 480px) {
  .ship-header {
    height: 45px;
    padding: 0 10px;
  }

  .header-center {
    display: none;
  }

  .nav-item span:last-child {
    display: none;
  }
}
</style>