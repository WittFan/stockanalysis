<template>
  <div class="chart-layout">
    <!-- 图表区 -->
    <div class="chart-panel">
      <div v-if="loading" class="loading-mask abs">
        <div class="spinner"></div>
        <span>加载数据中…</span>
      </div>
      <div v-if="error" class="error-box">{{ error }}</div>
      <EChartsWrapper :option="chartOption" style="height:100%;" />
    </div>

    <!-- 右侧面板（Apple grouped list 风格） -->
    <div class="side-panel">
      <!-- 周期选择 -->
      <div class="side-section">
        <div class="section-label">时间范围</div>
        <div class="seg-ctrl">
          <button
            v-for="p in [1,2,3]" :key="p"
            class="seg-btn" :class="{ active: period === p }"
            @click="setPeriod(p)"
          >近 {{ p }} 年</button>
        </div>
      </div>

      <!-- 搜索 -->
      <div class="side-section">
        <div class="search-wrap">
          <svg class="search-icon" viewBox="0 0 16 16" fill="none">
            <circle cx="6.5" cy="6.5" r="5" stroke="currentColor" stroke-width="1.3"/>
            <path d="M10.5 10.5L14 14" stroke="currentColor" stroke-width="1.3" stroke-linecap="round"/>
          </svg>
          <input v-model="search" class="search-input" type="text" placeholder="搜索股票名称或代码" />
          <button v-if="search" class="search-clear" @click="search = ''">✕</button>
        </div>
      </div>

      <!-- 批量操作 -->
      <div class="side-section side-actions">
        <button class="action-btn" @click="setAll(true)">全选</button>
        <span class="action-sep"></span>
        <button class="action-btn" @click="setAll(false)">全不选</button>
        <span class="action-sep"></span>
        <button class="action-btn" @click="invertAll()">反选</button>
      </div>

      <!-- 股票列表 -->
      <div class="stock-list">
        <label v-for="m in filteredMeta" :key="m.sym" class="stock-row">
          <input type="checkbox" class="stock-cb" :checked="visible[m.sym]" @change="toggleLine(m)" />
          <span class="stock-dot" :style="{ background: m.color }"></span>
          <span class="stock-info">
            <span class="stock-name">{{ m.name }}</span>
            <span class="stock-code">{{ m.sym }}</span>
          </span>
        </label>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import EChartsWrapper from '@/components/EChartsWrapper.vue'

const period  = ref(3)
const loading = ref(true)
const error   = ref('')
const search  = ref('')
const visible = ref({})
const dates   = ref([])
const series  = ref([])

const filteredMeta = computed(() => {
  const q = search.value.toLowerCase().trim()
  if (!q) return series.value
  return series.value.filter(m =>
    m.name.toLowerCase().includes(q) || m.sym.toLowerCase().includes(q)
  )
})

const chartOption = computed(() => ({
  backgroundColor: '#ffffff',
  tooltip: {
    trigger: 'axis',
    confine: true,
    backgroundColor: 'rgba(255,255,255,0.92)',
    borderColor: '#e5e5ea',
    borderWidth: 0.5,
    textStyle: { color: '#1c1c1e', fontSize: 12 },
    formatter: params => {
      const d = params[0]?.axisValueLabel || ''
      const lines = params.slice(0, 8).map(p =>
        `<span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};margin-right:5px;"></span>${p.seriesName}：${p.data[1]?.toFixed(4) ?? '-'}`
      )
      if (params.length > 8) lines.push(`<span style="color:#8e8e93">…另 ${params.length - 8} 只</span>`)
      return `<div style="font-size:11px;color:#8e8e93;margin-bottom:4px">${d}</div>${lines.join('<br>')}`
    },
  },
  grid: { top: 16, bottom: 32, left: 52, right: 16 },
  xAxis: {
    type: 'time',
    axisLine: { lineStyle: { color: '#e5e5ea', width: 0.5 } },
    axisTick: { lineStyle: { color: '#e5e5ea' } },
    axisLabel: { color: '#8e8e93', fontSize: 11 },
    splitLine: { show: false },
  },
  yAxis: {
    type: 'value',
    name: '归一化（起始=1.0）',
    nameTextStyle: { color: '#8e8e93', fontSize: 11 },
    axisLabel: { color: '#8e8e93', fontSize: 11 },
    axisLine: { show: false },
    axisTick: { show: false },
    splitLine: { lineStyle: { color: '#f2f2f7', width: 1 } },
  },
  series: series.value
    .filter(s => visible.value[s.sym])
    .map(s => ({
      type: 'line',
      name: s.name,
      data: dates.value.map((d, i) => [d, s.values[i]]),
      lineStyle: { color: s.color, width: 1.2 },
      itemStyle: { color: s.color },
      symbol: 'none',
    })),
}))

async function fetchChart(p) {
  loading.value = true
  error.value   = ''
  try {
    const res  = await fetch(`/api/chart?period=${p}`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    dates.value  = data.dates
    series.value = data.series
    const v = {}
    data.series.forEach(s => { v[s.sym] = true })
    visible.value = v
  } catch (e) {
    error.value = `加载失败：${e.message}`
  } finally {
    loading.value = false
  }
}

function toggleLine(m) { visible.value = { ...visible.value, [m.sym]: !visible.value[m.sym] } }
function setAll(checked) {
  const v = { ...visible.value }
  filteredMeta.value.forEach(m => { v[m.sym] = checked })
  visible.value = v
}
function invertAll() {
  const v = { ...visible.value }
  filteredMeta.value.forEach(m => { v[m.sym] = !v[m.sym] })
  visible.value = v
}
function setPeriod(p) { period.value = p; fetchChart(p) }
onMounted(() => fetchChart(period.value))
</script>

<style scoped>
.chart-layout {
  display: flex;
  position: fixed;
  top: var(--nav-height); left: 0; right: 0; bottom: 0;
  background: var(--bg-secondary);
}

/* ── 图表区 ── */
.chart-panel {
  flex: 1;
  background: var(--bg-primary);
  position: relative;
  overflow: hidden;
}

/* ── 右侧面板 ── */
.side-panel {
  width: 220px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-left: 0.5px solid var(--separator-opaque);
  overflow: hidden;
}

.side-section {
  padding: var(--space-3) var(--space-4);
  border-bottom: 0.5px solid var(--separator-opaque);
}

.section-label {
  font-size: var(--size-xs);
  font-weight: 500;
  color: var(--label-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

/* Chart.vue 的 seg-btn 需要占满宽度 */
.seg-btn { flex: 1; }

/* ── 搜索框（Apple 风格：灰底无边框） ── */
.search-wrap {
  display: flex;
  align-items: center;
  background: var(--fill-3);
  border-radius: var(--radius-sm);
  padding: 0 var(--space-2);
  gap: var(--space-1);
  height: 28px;
}

.search-icon {
  width: 13px;
  height: 13px;
  color: var(--label-muted);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--size-sm);
  font-family: inherit;
  color: var(--label);
  outline: none;
  min-width: 0;
}
.search-input::placeholder { color: var(--label-muted); }

.search-clear {
  border: none;
  background: var(--gray-3);
  color: var(--bg-primary);
  border-radius: 50%;
  width: 14px;
  height: 14px;
  font-size: 9px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

/* ── 批量操作 ── */
.side-actions {
  display: flex;
  align-items: center;
  gap: 0;
  padding: var(--space-2) var(--space-4);
}

.action-btn {
  flex: 1;
  border: none;
  background: transparent;
  color: var(--accent);
  font-size: var(--size-xs);
  font-family: inherit;
  cursor: pointer;
  padding: var(--space-1) 0;
  text-align: center;
}
.action-btn:hover { opacity: .7; }

.action-sep {
  width: 0.5px;
  height: 12px;
  background: var(--separator);
}

/* ── 股票列表 ── */
.stock-list {
  flex: 1;
  overflow-y: auto;
}

.stock-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 6px var(--space-4);
  cursor: pointer;
  border-bottom: 0.5px solid var(--separator-opaque);
  transition: background .1s;
}
.stock-row:hover { background: var(--fill-2); }

.stock-cb { display: none; }

/* 自定义 checkbox */
.stock-row input[type=checkbox] {
  display: block;
  width: 16px;
  height: 16px;
  accent-color: var(--accent);
  cursor: pointer;
  flex-shrink: 0;
}

.stock-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.stock-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.stock-name {
  font-size: var(--size-sm);
  color: var(--label);
  font-weight: 400;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.stock-code {
  font-size: var(--size-xs);
  color: var(--label-muted);
  margin-top: 1px;
}
</style>
