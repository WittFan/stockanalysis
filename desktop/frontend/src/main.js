import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import './style.css'

// 在 Vue 挂载前初始化字体缩放，避免首帧字号闪烁
import { useFontScale } from '@/composables/useFontScale.js'
useFontScale()

createApp(App).use(router).mount('#app')
