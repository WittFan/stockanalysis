<template>
  <!--
    导航栏设计参考 Apple HIG：
    - 高度 44px（Apple 规范）
    - 白底毛玻璃（backdrop-filter blur）
    - 产品名 + 分隔线 + 菜单，全部靠左
    - 激活项用 accent 蓝色，无背景高亮
    - 0.5px 底部分隔线（Apple 精细分隔线规范）
    - 右侧字体大小切换（A⁻ / A / A⁺），自动检测屏幕，手动可覆盖
  -->
  <nav class="sa-nav">
    <RouterLink to="/assistant" class="nav-btn" :class="{ active: route.path === '/assistant' }">助理</RouterLink>
    <RouterLink to="/value"     class="nav-btn" :class="{ active: route.path === '/value' }">价值坐标系</RouterLink>
    <RouterLink to="/chart"     class="nav-btn" :class="{ active: route.path === '/chart' }">趋势图</RouterLink>
    <RouterLink to="/industry"  class="nav-btn" :class="{ active: route.path === '/industry' }">行业分组</RouterLink>
    <RouterLink to="/backtest"  class="nav-btn" :class="{ active: route.path === '/backtest' }">回测</RouterLink>
    <RouterLink to="/download"  class="nav-btn" :class="{ active: route.path === '/download' }">数据管理</RouterLink>
    <RouterLink to="/settings"  class="nav-btn nav-btn--settings" :class="{ active: route.path === '/settings' }">设置</RouterLink>
  </nav>
  <div class="sa-page">
    <RouterView />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, RouterLink, RouterView } from 'vue-router'

const route = useRoute()

onMounted(() => {
  // Electron 桌面端：在 <html> 上加 is-electron 类
  // 用于 CSS 针对性地为交通灯按钮区域腾出空间
  if (window.electronAPI?.isElectron) {
    document.documentElement.classList.add('is-electron')
  }
})
</script>

<style scoped>
</style>
