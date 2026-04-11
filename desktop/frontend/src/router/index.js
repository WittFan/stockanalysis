import { createRouter, createWebHistory } from 'vue-router'
import Chart    from '@/views/Chart.vue'
import Industry from '@/views/Industry.vue'
import Backtest from '@/views/Backtest.vue'
import Value    from '@/views/Value.vue'

const routes = [
  { path: '/',         redirect: '/chart' },
  { path: '/chart',    component: Chart,    meta: { title: '股票池趋势图' } },
  { path: '/industry', component: Industry, meta: { title: '行业分组图' } },
  { path: '/backtest', component: Backtest, meta: { title: '策略回测' } },
  { path: '/value',    component: Value,    meta: { title: '价值坐标系' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title} · 量化投研` : '量化投研平台'
})

export default router
