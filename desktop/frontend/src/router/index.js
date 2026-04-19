import { createRouter, createWebHistory } from 'vue-router'

// 路由懒加载：按页面拆分 chunk，避免首屏加载 2MB 完整 bundle
const Chart     = () => import('@/views/Chart.vue')
const Industry  = () => import('@/views/Industry.vue')
const Backtest  = () => import('@/views/Backtest.vue')
const Value     = () => import('@/views/Value.vue')
const Download  = () => import('@/views/Download.vue')
const Assistant = () => import('@/views/Assistant.vue')
const Settings  = () => import('@/views/Settings.vue')

const routes = [
  { path: '/',           redirect: '/assistant' },
  { path: '/chart',      component: Chart,     meta: { title: '股票池趋势图' } },
  { path: '/industry',   component: Industry,  meta: { title: '行业分组图' } },
  { path: '/backtest',   component: Backtest,  meta: { title: '策略回测' } },
  { path: '/value',      component: Value,     meta: { title: '价值坐标系' } },
  { path: '/download',   component: Download,  meta: { title: '数据管理' } },
  { path: '/assistant',  component: Assistant, meta: { title: '助理' } },
  { path: '/settings',   component: Settings,  meta: { title: '设置' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 量化投研` : '量化投研平台'
})

export default router
