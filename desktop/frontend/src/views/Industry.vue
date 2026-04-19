<template>
  <div class="ind-layout">
    <!-- 顶部周期栏（Apple toolbar 风格） -->
    <div class="toolbar">
      <span class="toolbar-label">时间范围</span>
      <div class="seg-ctrl">
        <button
          v-for="p in [1,2,3]" :key="p"
          class="seg-btn" :class="{ active: period === p }"
          @click="setPeriod(p)"
        >近 {{ p }} 年</button>
      </div>
      <span class="toolbar-total" v-if="groups.length">共 {{ groups.length }} 个行业</span>
    </div>

    <!-- 内容区 -->
    <div class="ind-body">
      <div v-if="loading" class="loading-mask" style="height:calc(100vh - 96px);">
        <div class="spinner"></div>
        <span>加载数据中…</span>
      </div>
      <div v-else-if="error" class="error-box">{{ error }}</div>
      <div v-else class="ind-grid">
        <div v-for="g in groups" :key="g.name" class="ind-card">
          <div class="ind-header">
            <span class="ind-name">{{ g.name }}</span>
            <span class="ind-badge">{{ g.count }} 只</span>
          </div>
          <EChartsWrapper :option="buildOption(g)" style="height:300px;" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import EChartsWrapper from '@/components/EChartsWrapper.vue'

const period  = ref(3)
const loading = ref(true)
const error   = ref('')
const dates   = ref([])
const groups  = ref([])

function buildOption(g) {
  return {
    backgroundColor: '#ffffff',
    tooltip: {
      trigger: 'axis',
      confine: true,
      backgroundColor: 'rgba(255,255,255,0.92)',
      borderColor: '#e5e5ea',
      borderWidth: 0.5,
      textStyle: { color: '#1c1c1e', fontSize: 11 },
      formatter: params => {
        const d = params[0]?.axisValueLabel || ''
        const lines = params.slice(0, 6).map(p =>
          `<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:${p.color};margin-right:4px;"></span>${p.seriesName}：${p.data[1]?.toFixed(4) ?? '-'}`
        )
        if (params.length > 6) lines.push(`<span style="color:#8e8e93">…另 ${params.length - 6} 只</span>`)
        return `<div style="font-size:10px;color:#8e8e93;margin-bottom:3px">${d}</div>${lines.join('<br>')}`
      },
    },
    legend: {
      show: true,
      type: 'scroll',
      bottom: 4,
      textStyle: { fontSize: 9, color: '#8e8e93' },
      itemHeight: 6,
      itemWidth: 12,
      pageIconSize: 8,
    },
    grid: { top: 12, bottom: 52, left: 44, right: 12 },
    xAxis: {
      type: 'time',
      axisLine: { lineStyle: { color: '#e5e5ea', width: 0.5 } },
      axisTick: { lineStyle: { color: '#e5e5ea' } },
      axisLabel: { color: '#8e8e93', fontSize: 10 },
      splitLine: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '归一化',
      nameTextStyle: { color: '#8e8e93', fontSize: 10 },
      axisLabel: { color: '#8e8e93', fontSize: 10 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f2f2f7', width: 1 } },
    },
    series: g.series.map(s => ({
      type: 'line',
      name: `${s.name}（${s.sym}）`,
      data: dates.value.map((d, i) => [d, s.values[i]]),
      lineStyle: { color: s.color, width: 1.2 },
      itemStyle: { color: s.color },
      symbol: 'none',
    })),
  }
}

async function fetchIndustry(p) {
  loading.value = true
  error.value   = ''
  groups.value  = []
  try {
    const res  = await fetch(`/api/industry?period=${p}`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    dates.value  = data.dates
    groups.value = data.groups
  } catch (e) {
    error.value = `加载失败：${e.message}`
  } finally {
    loading.value = false
  }
}

function setPeriod(p) { period.value = p; fetchIndustry(p) }
onMounted(() => fetchIndustry(period.value))
</script>

<style scoped>
/* ── 整体布局 ── */
.ind-layout {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--nav-height));
}

/* ── 顶部工具栏（Apple 风格次级导航条） ── */
.toolbar {
  position: fixed;
  top: var(--nav-height); left: 0; right: 0;
  z-index: 100;
  height: 44px;
  background: rgba(255,255,255,0.88);
  backdrop-filter: blur(12px) saturate(1.6);
  -webkit-backdrop-filter: blur(12px) saturate(1.6);
  border-bottom: 0.5px solid var(--separator-opaque);
  display: flex;
  align-items: center;
  gap: var(--space-4);
  padding: 0 var(--space-5);
}

.toolbar-label {
  font-size: var(--size-xs);
  font-weight: 500;
  color: var(--label-muted);
  letter-spacing: 0.04em;
  text-transform: uppercase;
  white-space: nowrap;
}

.toolbar-total {
  font-size: var(--size-xs);
  color: var(--label-muted);
  margin-left: auto;
}

/* ── 内容区 ── */
.ind-body {
  padding-top: 44px; /* toolbar 高度 */
  overflow-y: auto;
  flex: 1;
}

/* ── 行业卡片网格 ── */
.ind-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--space-4);
  padding: var(--space-4) var(--space-5) var(--space-8);
}

/* ── 行业卡片（Apple 卡片：白底 + 10px 圆角 + 极轻阴影） ── */
.ind-card {
  background: var(--bg-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}

.ind-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border-bottom: 0.5px solid var(--separator-opaque);
}

.ind-name {
  font-size: var(--size-sm);
  font-weight: 600;
  color: var(--label);
  letter-spacing: var(--tracking-body);
}

.ind-badge {
  font-size: var(--size-xs);
  color: var(--label-muted);
  background: var(--fill-3);
  border-radius: 20px;
  padding: 1px 7px;
  font-weight: 400;
}

@media (max-width: 900px) {
  .ind-grid { grid-template-columns: 1fr; }
}
</style>
