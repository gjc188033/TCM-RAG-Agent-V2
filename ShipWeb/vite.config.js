import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    proxy: {
      '/conversations': {
        target: 'http://localhost:9978',
        changeOrigin: true,
        secure: false
      },
      '/model_status': {
        target: 'http://localhost:9978',
        changeOrigin: true,
        secure: false
      },
      '/booksname': {
        target: 'http://localhost:9978',
        changeOrigin: true,
        secure: false
      }
    }
  }
})
