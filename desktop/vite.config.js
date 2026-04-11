import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ command }) => ({
  // Vite 项目根目录指向 frontend/ 子目录
  root: 'frontend',
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./frontend/src', import.meta.url)),
    },
  },
  // Electron 生产模式加载 file:// 协议，需相对路径
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
    // 产物输出到 frontend/dist/（相对于 root: 'frontend'）
    outDir: 'dist',
    emptyOutDir: true,
  },
}))
