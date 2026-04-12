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
    <span class="logo">大道量化投研平台</span>
    <span class="nav-sep"></span>
    <RouterLink to="/chart"    class="nav-btn" :class="{ active: route.path === '/chart' }">趋势图</RouterLink>
    <RouterLink to="/industry" class="nav-btn" :class="{ active: route.path === '/industry' }">行业分组</RouterLink>
    <RouterLink to="/backtest" class="nav-btn" :class="{ active: route.path === '/backtest' }">回测</RouterLink>
    <RouterLink to="/value"    class="nav-btn" :class="{ active: route.path === '/value' }">价值坐标系</RouterLink>
    <RouterLink to="/download" class="nav-btn" :class="{ active: route.path === '/download' }">数据管理</RouterLink>

    <!-- 字体大小切换（右侧对齐） -->
    <div class="font-ctrl">
      <button
        v-for="l in levels" :key="l"
        class="font-btn"
        :class="{ active: level === l }"
        :title="{ small: '缩小字体', medium: '默认字体', large: '放大字体' }[l]"
        @click="setLevel(l)"
      >{{ labels[l] }}</button>
    </div>
  </nav>
  <div class="sa-page">
    <RouterView />
  </div>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRoute, RouterLink, RouterView } from 'vue-router'
import { useFontScale } from '@/composables/useFontScale.js'

const route = useRoute()
const { level, setLevel, levels, labels } = useFontScale()

onMounted(() => {
  // Electron 桌面端：在 <html> 上加 is-electron 类
  // 用于 CSS 针对性地为交通灯按钮区域腾出空间
  if (window.electronAPI?.isElectron) {
    document.documentElement.classList.add('is-electron')
  }
})
</script>

<style scoped>
/* 字体切换控件 — 靠右 */
.font-ctrl {
  display: flex;
  align-items: center;
  gap: 1px;
  margin-left: auto;
  background: var(--fill-3);
  border-radius: var(--radius-sm);
  padding: 2px;
}

.font-btn {
  height: 22px;
  min-width: 26px;
  padding: 0 5px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--label-muted);
  font-family: inherit;
  font-weight: 400;
  cursor: pointer;
  transition: background .12s, color .12s, box-shadow .12s;
  line-height: 1;
  /* 三个按钮字号不同，体现"大中小"含义 */
}
.font-btn:nth-child(1) { font-size: 10px; }  /* A⁻ */
.font-btn:nth-child(2) { font-size: 12px; }  /* A  */
.font-btn:nth-child(3) { font-size: 14px; }  /* A⁺ */

.font-btn:hover { background: var(--fill-4); color: var(--label); }

.font-btn.active {
  background: var(--bg-primary);
  color: var(--accent);
  font-weight: 600;
  box-shadow: var(--shadow-xs);
}
</style>
