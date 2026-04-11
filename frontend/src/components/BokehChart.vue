<template>
  <div ref="container" class="bokeh-container"></div>
</template>

<script setup>
/**
 * BokehChart 组件
 * 接收后端返回的 {script, div}，动态注入 DOM 渲染 Bokeh 图表。
 * 迁移自原 value_matrix_handler.py 中的 applyChart() JS 函数。
 */
import { ref, watch, onBeforeUnmount } from 'vue'

const props = defineProps({
  script: { type: String, default: '' },
  div:    { type: String, default: '' },
})

const container = ref(null)

// 追踪动态插入的 <script> 节点，组件销毁时清理
const injectedScripts = []

function applyChart(script, div) {
  if (!container.value) return

  // 清理旧图表和脚本
  container.value.innerHTML = ''
  injectedScripts.forEach(s => s.remove())
  injectedScripts.length = 0

  if (!div) return

  // 注入 div
  container.value.innerHTML = div

  // 解析并执行 script 标签
  const tmp = document.createElement('div')
  tmp.innerHTML = script
  tmp.querySelectorAll('script').forEach(s => {
    const ns = document.createElement('script')
    if (s.src) {
      ns.src = s.src
    } else {
      ns.textContent = s.textContent
    }
    document.head.appendChild(ns)
    injectedScripts.push(ns)
  })
}

// flush: 'post' 确保 DOM 挂载后再执行，container.value 才不为 null
watch(() => [props.script, props.div], ([script, div]) => {
  applyChart(script, div)
}, { immediate: true, flush: 'post' })

onBeforeUnmount(() => {
  injectedScripts.forEach(s => s.remove())
})
</script>

<style scoped>
.bokeh-container {
  width: 100%;
  height: 100%;
}
/* 让 Bokeh 撑满容器 */
.bokeh-container :deep(.bk-root) {
  width: 100% !important;
  height: 100% !important;
}
</style>
