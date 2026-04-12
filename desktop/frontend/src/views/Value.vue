<template>
  <div class="value-layout">
    <!-- 左侧控制面板（Apple grouped list 风格） -->
    <div class="ctrl-panel">

      <!-- 显示模式 -->
      <div class="ctrl-section">
        <div class="section-label">显示模式</div>
        <div class="seg-ctrl">
          <button class="seg-btn" :class="{ active: mode === 'past' }"     @click="setMode('past')">过去</button>
          <button class="seg-btn" :class="{ active: mode === 'forecast' }" @click="setMode('forecast')">预期未来</button>
        </div>
      </div>

      <!-- 报告年度（仅过去模式） -->
      <div v-if="mode === 'past'" class="ctrl-section">
        <div class="section-label">报告年度</div>
        <div class="year-list">
          <button
            v-for="item in YEAR_ITEMS" :key="item.val"
            class="year-btn" :class="{ active: year === item.val }"
            @click="year = item.val; fetchData()"
          >{{ item.label }}</button>
        </div>
        <!-- 近5年时显示实际年份范围 -->
        <div v-if="year === '5y' && yearRange" class="year-range-hint">
          {{ yearRange[0] }} – {{ yearRange[1] }} 年均值
        </div>
      </div>

      <!-- 景气度指标（Y 轴） -->
      <div class="ctrl-section">
        <div class="section-label">景气度指标（Y 轴）</div>
        <div class="year-list">
          <button class="year-btn active">营收增长率</button>
        </div>
      </div>

      <!-- 竞争力指标（X 轴） -->
      <div class="ctrl-section">
        <div class="section-label">竞争力指标（X 轴）</div>
        <div class="radio-group">
          <label class="radio-row">
            <input type="radio" class="radio-inp" v-model="metric" value="gross" @change="onMetricChange">
            <span class="radio-label">销售毛利率</span>
          </label>
          <label class="radio-row">
            <input type="radio" class="radio-inp" v-model="metric" value="net" @change="onMetricChange">
            <span class="radio-label">销售净利率</span>
          </label>
        </div>
      </div>

      <!-- 预期模式输入表格 -->
      <div v-if="mode === 'forecast'" class="ctrl-section fc-section">
        <div class="section-label">输入预期数据（%）</div>
        <table class="fc-table">
          <thead>
            <tr>
              <th class="th">股票</th>
              <th class="th">竞争力</th>
              <th class="th">增长率</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in fcStocks" :key="s.code" class="fc-row">
              <td class="td td-name" :title="`${s.name}（${s.code}）`">
                <span class="fc-name">{{ s.name }}</span>
                <span class="fc-code">{{ s.code }}</span>
              </td>
              <td class="td"><input type="number" class="fc-inp" v-model.number="s.x" @input="debounceForecast" /></td>
              <td class="td"><input type="number" class="fc-inp" v-model.number="s.y" @input="debounceForecast" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="chart-panel">
      <div v-if="loading" class="loading-mask abs">
        <div class="spinner"></div>
        <div>正在从 Tushare 获取财务数据…</div>
        <div class="loading-sub">首次加载约需 1 分钟，后续从缓存读取</div>
      </div>
      <div v-if="error" class="error-box" style="position:absolute;top:20px;left:50%;transform:translateX(-50%);z-index:10;white-space:nowrap;">{{ error }}</div>
      <EChartsWrapper :option="chartOption" style="height:100%;" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import EChartsWrapper from '@/components/EChartsWrapper.vue'

// 年份列表：单年 + 近5年聚合
const YEAR_ITEMS = [
  { val: '5y',  label: '近 5 年' },
  { val: 2024,  label: '2024 年报' },
  { val: 2023,  label: '2023 年报' },
  { val: 2022,  label: '2022 年报' },
  { val: 2021,  label: '2021 年报' },
  { val: 2020,  label: '2020 年报' },
]

const mode      = ref('past')
const year      = ref('5y')          // 默认选近5年
const yearRange = ref(null)          // 后端返回的 [startYear, endYear]，近5年模式专用
const metric    = ref('gross')
const loading   = ref(false)
const error     = ref('')
const stocks    = ref([])
const fcStocks  = ref([])

let fcTimer = null

const chartOption = computed(() => {
  const metricName = metric.value === 'gross' ? '销售毛利率' : '销售净利率'
  const is5y       = year.value === '5y'
  const xLabel     = is5y && mode.value === 'past'
    ? `近5年${metricName}（算数平均）(%)`
    : `${metricName}(%)`

  let titleText
  if (mode.value === 'forecast') {
    titleText = `价值坐标系 · 预期未来 · ${metricName}`
  } else if (is5y && yearRange.value) {
    titleText = `价值坐标系 · 近5年均值（${yearRange.value[0]}–${yearRange.value[1]}）· ${metricName}`
  } else if (is5y) {
    titleText = `价值坐标系 · 近5年均值 · ${metricName}`
  } else {
    titleText = `价值坐标系 · ${year.value} 年报 · ${metricName}`
  }

  const yAxisName = is5y && mode.value === 'past'
    ? '近5年营收增长率（几何平均）(%)'
    : '营业收入同比增长率(%)'

  return {
    backgroundColor: '#ffffff',
    title: {
      text: titleText,
      textStyle: {
        fontSize: 15,
        fontWeight: 600,
        color: '#1c1c1e',
        fontFamily: '-apple-system, "SF Pro Display", "Helvetica Neue", Helvetica, Arial, sans-serif',
      },
      top: 16,
      left: 20,
    },
    tooltip: {
      backgroundColor: 'rgba(255,255,255,0.92)',
      borderColor: '#e5e5ea',
      borderWidth: 0.5,
      textStyle: { color: '#1c1c1e', fontSize: 13 },
      formatter: p => `<b style="color:#1c1c1e">${p.data[2]}</b><br><span style="color:#8e8e93;font-size:12px">${p.data[3]}</span><br>${xLabel}：<b>${p.data[0]}%</b><br>营收增长率：<b>${p.data[1]}%</b>`,
    },
    xAxis: {
      type: 'value',
      name: xLabel,
      nameLocation: 'middle',
      nameGap: 32,
      nameTextStyle: { color: '#8e8e93', fontSize: 13 },
      axisLabel: { color: '#8e8e93', fontSize: 13 },
      axisLine: { lineStyle: { color: '#e5e5ea', width: 0.5 } },
      axisTick: { lineStyle: { color: '#e5e5ea' } },
      splitLine: { lineStyle: { color: '#f2f2f7', width: 1 } },
    },
    yAxis: {
      type: 'value',
      name: yAxisName,
      nameLocation: 'middle',
      nameGap: 60,
      nameTextStyle: { color: '#8e8e93', fontSize: 13 },
      axisLabel: { color: '#8e8e93', fontSize: 13 },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { lineStyle: { color: '#f2f2f7', width: 1 } },
    },
    grid: { top: 60, bottom: 58, left: 80, right: 24 },
    series: [{
      type: 'scatter',
      data: stocks.value.map(s => [s.x, s.y, s.name, s.code]),
      symbolSize: 11,
      itemStyle: { color: '#007aff', opacity: 0.75 },
      emphasis: { itemStyle: { color: '#5856d6', opacity: 1 }, scale: 1.4 },
      label: {
        show: true,
        formatter: p => p.data[2],
        fontSize: 11,
        color: '#3c3c43',
        position: 'right',
      },
      markLine: {
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#c6c6c8', type: 'dashed', width: 0.8 },
        data: [{ xAxis: 0 }, { yAxis: 0 }],
      },
    }],
  }
})

async function fetchData() {
  loading.value = true
  error.value   = ''
  yearRange.value = null
  try {
    const res  = await fetch(`/api/value/data?year=${year.value}&metric=${metric.value}`)
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    stocks.value    = data.stocks || []
    fcStocks.value  = stocks.value.map(s => ({ ...s }))
    // 近5年模式后端会返回 year_range: [2021, 2025]
    if (data.year_range) yearRange.value = data.year_range
  } catch (e) {
    error.value = `加载失败：${e.message}`
  } finally {
    loading.value = false
  }
}

async function submitForecast() {
  const payload = fcStocks.value
    .filter(s => s.x != null && s.y != null && !isNaN(s.x) && !isNaN(s.y))
    .map(s => ({ code: s.code, name: s.name, x: Math.round(s.x), y: Math.round(s.y) }))
  if (!payload.length) return

  loading.value = true
  error.value   = ''
  try {
    const res  = await fetch('/api/value/forecast', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ metric: metric.value, stocks: payload }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    stocks.value = data.stocks || []
  } catch (e) {
    error.value = `生成失败：${e.message}`
  } finally {
    loading.value = false
  }
}

function debounceForecast() {
  clearTimeout(fcTimer)
  fcTimer = setTimeout(submitForecast, 600)
}

function setMode(m) {
  mode.value = m
  if (m === 'forecast') {
    if (!fcStocks.value.length) fetchData().then(() => submitForecast())
    else submitForecast()
  } else {
    fetchData()
  }
}

function onMetricChange() {
  if (mode.value === 'past') fetchData()
  else submitForecast()
}

onMounted(() => fetchData())
</script>

<style scoped>
/* ── 整体布局 ── */
.value-layout {
  display: flex;
  position: fixed;
  top: var(--nav-height); left: 0; right: 0; bottom: 0;
  background: var(--bg-secondary);
}

/* ── 左侧控制面板 ── */
.ctrl-panel {
  width: 220px;
  flex-shrink: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--bg-secondary);
  border-right: 0.5px solid var(--separator-opaque);
  overflow-y: auto;
  overflow-x: hidden;
}

.ctrl-section {
  padding: var(--space-3) var(--space-4);
  border-bottom: 0.5px solid var(--separator-opaque);
  flex-shrink: 0;
}

.fc-section {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.section-label {
  font-size: var(--size-xs);
  font-weight: 500;
  color: var(--label-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  margin-bottom: var(--space-2);
}

/* ── Segmented Control ── */
.seg-ctrl {
  display: flex;
  background: var(--fill-3);
  border-radius: var(--radius-sm);
  padding: 2px;
  gap: 2px;
}

.seg-btn {
  flex: 1;
  height: 24px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--label);
  font-size: var(--size-xs);
  font-family: inherit;
  font-weight: 400;
  cursor: pointer;
  transition: background .12s, box-shadow .12s;
}
.seg-btn:hover { background: var(--fill-4); }
.seg-btn.active {
  background: var(--bg-primary);
  box-shadow: var(--shadow-xs);
  font-weight: 500;
}

/* ── 年度列表 ── */
.year-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.year-range-hint {
  margin-top: var(--space-2);
  font-size: var(--size-xs);
  color: var(--label-muted);
  text-align: center;
  letter-spacing: 0.01em;
}

.year-btn {
  width: 100%;
  text-align: left;
  padding: 5px var(--space-2);
  border: none;
  border-radius: var(--radius-xs);
  background: transparent;
  color: var(--label);
  font-size: var(--size-sm);
  font-family: inherit;
  cursor: pointer;
  transition: background .1s;
}
.year-btn:hover { background: var(--fill-2); }
.year-btn.active {
  background: var(--accent);
  color: #fff;
  font-weight: 500;
}

/* ── 单选组 ── */
.radio-group {
  display: flex;
  flex-direction: column;
  gap: var(--space-1);
}

.radio-row {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 4px 0;
  cursor: pointer;
}

.radio-inp { accent-color: var(--accent); cursor: pointer; }

.radio-label {
  font-size: var(--size-sm);
  color: var(--label);
}

/* ── 预期表格 ── */
.fc-table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--size-xs);
}

.th {
  position: sticky;
  top: 0;
  background: var(--bg-secondary);
  border-bottom: 0.5px solid var(--separator-opaque);
  padding: 5px var(--space-1);
  font-size: 10px;
  color: var(--label-muted);
  text-align: center;
  font-weight: 500;
  white-space: nowrap;
}

.td {
  padding: 3px var(--space-1);
  border-bottom: 0.5px solid var(--separator-opaque);
  vertical-align: middle;
}

.fc-row:last-child .td { border-bottom: none; }

.td-name {
  max-width: 72px;
  display: flex;
  flex-direction: column;
}

.fc-name {
  font-size: 11px;
  color: var(--label);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fc-code {
  font-size: 9px;
  color: var(--label-muted);
}

.fc-inp {
  width: 100%;
  padding: 3px 4px;
  border: 0.5px solid var(--separator-opaque);
  border-radius: var(--radius-xs);
  font-size: 11px;
  font-family: inherit;
  text-align: right;
  color: var(--label);
  background: var(--bg-primary);
  outline: none;
  transition: border-color .15s;
}
.fc-inp:focus { border-color: var(--accent); }

/* ── 图表区 ── */
.chart-panel {
  flex: 1;
  height: 100%;
  overflow: hidden;
  position: relative;
  background: var(--bg-primary);
}

.loading-sub {
  font-size: var(--size-xs);
  color: var(--label-muted);
  margin-top: -4px;
}
</style>
