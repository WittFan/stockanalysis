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
      // LLM API 代理（解决浏览器开发模式 CORS 限制）
      '/proxy/openai': {
        target: 'https://api.openai.com',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/proxy\/openai/, ''),
      },
      '/proxy/kimi': {
        target: 'https://api.kimi.com',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/proxy\/kimi/, ''),
        secure: true,
      },
      '/proxy/anthropic': {
        target: 'https://api.anthropic.com',
        changeOrigin: true,
        rewrite: path => path.replace(/^\/proxy\/anthropic/, ''),
      },
    },
  },
  build: {
    // 产物输出到 frontend/dist/（相对于 root: 'frontend'）
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          // 将 Three.js + VRM 拆分为独立 chunk，避免主 bundle 过大
          if (id.includes('node_modules/three') || id.includes('node_modules/@pixiv/three-vrm')) {
            return 'three-vrm'
          }
          // 将 echarts 拆分为独立 chunk
          if (id.includes('node_modules/echarts')) {
            return 'echarts'
          }
          // Vue 生态单独打包
          if (id.includes('node_modules/vue') || id.includes('node_modules/vue-router')) {
            return 'vue'
          }
        },
      },
    },
  },
}))
