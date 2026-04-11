import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ command }) => ({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  // Electron 生产模式加载 file:// 协议的本地 HTML，需要相对路径
  // 开发模式（npm run dev）保持 '/'
  base: command === 'build' ? './' : '/',
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8888',
        changeOrigin: true,
      },
    },
  },
  build: {
    // 生产构建产物输出到 dist/
    outDir: 'dist',
    // 清空旧产物
    emptyOutDir: true,
  },
}))
