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
  loading_message: "正在加载中医数据库模型..."
})

// 配置marked
marked.setOptions({
  highlight: function (code, lang) {
    return code // 简化处理，后续可以集成代码高亮
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

    // 立即执行一次
    await checkModelStatus()

    // 设置定时器，每10秒检查一次状态
    setInterval(checkModelStatus, 10000)
  } catch (error) {
    console.error('启动模型状态轮询失败:', error)
  }
}

// 初始化应用
onMounted(async () => {
  try {
    console.log('初始化杏林智慧应用...')

    // 启动模型状态轮询
    await startModelStatusPolling()

    console.log('应用初始化完成')
  } catch (error) {
    console.error('应用初始化失败:', error)
    ElMessage.error('应用初始化失败，请刷新页面重试')
  }
})
</script>




<template>
  <div class="tcm-app">
    <!-- 顶部导航栏 -->
    <header class="tcm-header">
      <div class="header-left">
        <div class="logo-section">
          <div class="logo-circle">
            <img src="/icon/img.png" alt="上海市七院中医智能体" />
          </div>
          <div class="logo-text">
            <h1>上海市七院中医智能体</h1>
            <p>专业中医诊疗，智能健康服务</p>
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
            <span>老中医在线</span>
          </div>
        </div>
      </div>

      <div class="header-right">
        <nav class="nav-menu">
          <button class="nav-item" :class="{ active: currentView === 'chat' }" @click="handleViewChange('chat')">
            <span class="nav-icon">💬</span>
            <span>问诊</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'records' }" @click="handleViewChange('records')">
            <span class="nav-icon">📋</span>
            <span>病历</span>
          </button>
          <button class="nav-item" :class="{ active: currentView === 'books' }" @click="handleViewChange('books')">
            <span class="nav-icon">📚</span>
            <span>典籍</span>
          </button>
          <button class="nav-item" @click="handleLogin">
            <span class="nav-icon">👤</span>
            <span>登录</span>
          </button>
        </nav>
      </div>
    </header>

    <!-- 主内容区域 -->
    <main class="tcm-main">
      <!-- 聊天视图 -->
      <div v-if="currentView === 'chat'" class="view-container">
        <ChatView />
      </div>

      <!-- 其他视图占位符 -->
      <div v-else class="view-container">
        <div class="coming-soon">
          <div class="coming-icon">🚧</div>
          <h2>功能开发中</h2>
          <p>{{ currentView === 'records' ? '病历管理' : currentView === 'books' ? '典籍查阅' : '用户登录' }}功能正在开发中，敬请期待...</p>
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
  font-family: 'Microsoft YaHei', '微软雅黑', '宋体', serif;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
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

/* 绿色清新主题色彩 */
:root {
  --tcm-primary: #059669;      /* 翠绿色 - 主色调 */
  --tcm-secondary: #10b981;    /* 绿色 - 辅助色 */
  --tcm-accent: #3b82f6;       /* 蓝色 - 强调色 */
  --tcm-light: #f0fdf4;        /* 浅绿色 - 浅色背景 */
  --tcm-dark: #064e3b;         /* 深绿色 - 深色文字 */
  --tcm-green: #22c55e;        /* 亮绿色 - 成功状态 */
  --tcm-red: #ef4444;          /* 红色 - 错误状态 */
  --tcm-shadow: rgba(5, 150, 105, 0.2);
}
</style>

<style scoped>
/* 应用主容器 */
.tcm-app {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  font-family: 'Microsoft YaHei', '微软雅黑', '宋体', serif;
}

/* 顶部导航栏 */
.tcm-header {
  height: 60px;
  background: linear-gradient(90deg, var(--tcm-primary) 0%, #047857 50%, var(--tcm-secondary) 100%);
  box-shadow: 0 4px 12px var(--tcm-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: relative;
  z-index: 100;
}

.tcm-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><path d="M0,10 Q25,0 50,10 T100,10 L100,20 L0,20 Z" fill="rgba(255,255,255,0.1)"/></svg>') repeat-x;
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
  border-radius: 50%;
  background: linear-gradient(45deg, var(--tcm-accent), #2563eb);
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 3px 6px rgba(0, 0, 0, 0.2);
  border: 2px solid rgba(255, 255, 255, 0.3);
}

.logo-circle img {
  width: 24px;
  height: 24px;
  object-fit: contain;
}

.logo-text h1 {
  color: var(--tcm-light);
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
  letter-spacing: 1.5px;
}

.logo-text p {
  color: rgba(255, 248, 220, 0.8);
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
  background: rgba(255, 255, 255, 0.15);
  padding: 6px 15px;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.status-loading, .status-ready {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tcm-light);
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
  color: rgba(255, 248, 220, 0.8);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s ease;
  font-size: 10px;
  min-width: 50px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--tcm-light);
  transform: translateY(-2px);
}

.nav-item.active {
  background: rgba(255, 215, 0, 0.2);
  color: var(--tcm-accent);
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.3);
}

.nav-icon {
  font-size: 14px;
}

/* 主内容区域 */
.tcm-main {
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
  color: var(--tcm-dark);
}

.coming-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.coming-soon h2 {
  color: var(--tcm-primary);
  font-size: 28px;
  margin-bottom: 15px;
}

.coming-soon p {
  color: #666;
  font-size: 16px;
}

/* 响应式设计 */
@media (max-width: 1024px) {
  .tcm-header {
    padding: 0 20px;
  }

  .logo-text h1 {
    font-size: 20px;
  }

  .nav-item {
    padding: 6px 12px;
    min-width: 55px;
  }
}

@media (max-width: 768px) {
  .tcm-header {
    height: 50px;
    padding: 0 15px;
    flex-wrap: wrap;
  }

  .header-left {
    flex: 0 0 auto;
  }

  .logo-circle {
    width: 98px;
    height: 98px;
  }

  .logo-circle img {
    width: 83px;
    height: 83px;
  }

  .logo-text h1 {
    font-size: 18px;
    letter-spacing: 1px;
  }

  .logo-text p {
    display: none;
  }

  .header-center {
    flex: 1;
    margin: 0 15px;
  }

  .clinic-status {
    padding: 6px 15px;
    font-size: 12px;
  }

  .header-right {
    flex: 0 0 auto;
  }

  .nav-menu {
    gap: 3px;
  }

  .nav-item {
    padding: 6px 10px;
    min-width: 45px;
    font-size: 10px;
  }

  .nav-icon {
    font-size: 16px;
  }

  .coming-soon {
    padding: 30px 20px;
  }

  .coming-icon {
    font-size: 60px;
  }

  .coming-soon h2 {
    font-size: 22px;
  }

  .coming-soon p {
    font-size: 14px;
  }
}

@media (max-width: 480px) {
  .tcm-header {
    height: 45px;
    padding: 0 10px;
  }

  .logo-section {
    gap: 8px;
  }

  .logo-circle {
    width: 75px;
    height: 75px;
  }

  .logo-circle img {
    width: 60px;
    height: 60px;
  }

  .logo-text h1 {
    font-size: 16px;
    letter-spacing: 0.5px;
  }

  .header-center {
    display: none;
  }

  .nav-item {
    padding: 4px 8px;
    min-width: 40px;
    font-size: 9px;
  }

  .nav-item span:last-child {
    display: none;
  }

  .nav-icon {
    font-size: 14px;
  }

  .tcm-main {
    height: calc(100vh - 45px);
  }

  .coming-soon {
    padding: 20px 15px;
  }

  .coming-icon {
    font-size: 50px;
    margin-bottom: 15px;
  }

  .coming-soon h2 {
    font-size: 18px;
    margin-bottom: 10px;
  }

  .coming-soon p {
    font-size: 12px;
  }
}

/* 超小屏幕优化 */
@media (max-width: 320px) {
  .tcm-header {
    height: 40px;
    padding: 0 8px;
  }

  .logo-text h1 {
    font-size: 14px;
  }

  .nav-menu {
    gap: 2px;
  }

  .nav-item {
    padding: 3px 6px;
    min-width: 35px;
  }

  .nav-icon {
    font-size: 12px;
  }

  .tcm-main {
    height: calc(100vh - 40px);
  }
}

/* 顶部导航栏 */
.tcm-header {
  height: 60px;
  background: linear-gradient(90deg, var(--tcm-primary) 0%, #A0522D 50%, var(--tcm-secondary) 100%);
  box-shadow: 0 4px 12px var(--tcm-shadow);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 20px;
  position: relative;
  z-index: 100;
}

.tcm-header::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: url('data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 20"><path d="M0,10 Q25,0 50,10 T100,10 L100,20 L0,20 Z" fill="rgba(255,255,255,0.1)"/></svg>') repeat-x;
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
  width: 75px;
  height: 75px;
  border-radius: 8px;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: none;
  border: none;
}

.logo-circle img {
  width: 60px;
  height: 60px;
  object-fit: contain;
  border-radius: 0;
  border: none;
}

.logo-text h1 {
  color: var(--tcm-light);
  font-size: 18px;
  font-weight: bold;
  margin: 0;
  text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
  letter-spacing: 1.5px;
}

.logo-text p {
  color: rgba(255, 248, 220, 0.8);
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
  background: rgba(255, 255, 255, 0.15);
  padding: 6px 15px;
  border-radius: 20px;
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.2);
}

.status-loading, .status-ready {
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--tcm-light);
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
  color: rgba(255, 248, 220, 0.8);
  cursor: pointer;
  border-radius: 10px;
  transition: all 0.3s ease;
  font-size: 10px;
  min-width: 50px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.15);
  color: var(--tcm-light);
  transform: translateY(-2px);
}

.nav-item.active {
  background: rgba(255, 215, 0, 0.2);
  color: var(--tcm-accent);
  box-shadow: 0 2px 8px rgba(255, 215, 0, 0.3);
}

.nav-icon {
  font-size: 14px;
}

/* 主内容区域 */
.tcm-main {
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
  color: var(--tcm-dark);
}

.coming-icon {
  font-size: 80px;
  margin-bottom: 20px;
}

.coming-soon h2 {
  color: var(--tcm-primary);
  font-size: 28px;
  margin-bottom: 15px;
}

.coming-soon p {
  color: #666;
  font-size: 16px;
}
</style>