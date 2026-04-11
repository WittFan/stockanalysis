<template>
  <div class="page-body">

    <!-- 策略列表 -->
    <template v-if="!resultHtml">
      <div class="page-header">
        <h1 class="page-title">策略项目</h1>
      </div>

      <div v-if="loadingList" class="loading-mask" style="height:200px;">
        <div class="spinner"></div>
      </div>
      <p v-else-if="strategies.length === 0" class="empty">
        data/projs/ 目录下暂无策略文件（*.toml）
      </p>

      <div v-else class="proj-grid">
        <div v-for="s in strategies" :key="s.file" class="proj-card">
          <div class="proj-meta">
            <div class="proj-name">{{ s.name }}</div>
            <div class="proj-file">{{ s.file }}</div>
          </div>
          <button
            class="run-btn"
            :class="{ 'run-btn--disabled': running }"
            :disabled="running"
            @click="runBacktest(s.file)"
          >
            <svg width="11" height="11" viewBox="0 0 11 11" fill="currentColor">
              <path d="M2 1.5L9 5.5L2 9.5V1.5Z"/>
            </svg>
            运行回测
          </button>
        </div>
      </div>

      <!-- 运行中蒙层 -->
      <Teleport to="body">
        <div v-if="running" class="overlay">
          <div class="overlay-card">
            <div class="spinner" style="width:28px;height:28px;border-width:2.5px;border-top-color:var(--accent);"></div>
            <div class="overlay-name">{{ runningName }}</div>
            <div class="overlay-sub">正在运行回测…</div>
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: progress + '%' }"></div>
            </div>
            <div class="overlay-pct">{{ progress }}%</div>
            <div v-if="runError" class="overlay-error">{{ runError }}</div>
          </div>
        </div>
      </Teleport>
    </template>

    <!-- 回测结果 -->
    <template v-else>
      <div class="result-bar">
        <button class="btn btn-primary" @click="resultHtml = ''">
          <svg width="9" height="14" viewBox="0 0 9 14" fill="currentColor" style="margin-right:4px;">
            <path d="M7.5 1L1.5 7L7.5 13" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          返回列表
        </button>
        <span class="result-title">{{ runningName }} · 回测结果</span>
      </div>
      <iframe class="result-frame" :srcdoc="resultHtml" sandbox="allow-scripts"></iframe>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const strategies  = ref([])
const loadingList = ref(true)
const running     = ref(false)
const runningName = ref('')
const progress    = ref(0)
const runError    = ref('')
const resultHtml  = ref('')

let pollTimer = null

async function fetchList() {
  loadingList.value = true
  try {
    const res  = await fetch('/api/backtest/list')
    const data = await res.json()
    strategies.value = data.strategies || []
  } catch (e) {
    console.error('获取策略列表失败', e)
  } finally {
    loadingList.value = false
  }
}

async function runBacktest(file) {
  running.value     = true
  runningName.value = file.replace('.toml', '')
  progress.value    = 0
  runError.value    = ''
  try {
    const res  = await fetch('/api/backtest/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ toml_name: file }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    pollStatus(data.task_id)
  } catch (e) {
    runError.value = `启动失败：${e.message}`
    running.value  = false
  }
}

function pollStatus(taskId) {
  pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`/api/backtest/status/${taskId}`)
      const data = await res.json()
      progress.value = Math.round((data.progress || 0) * 100)
      if (data.status === 'done') { clearInterval(pollTimer); fetchResult(taskId) }
      else if (data.status === 'error') {
        clearInterval(pollTimer)
        runError.value = data.error || '回测出错'
        running.value  = false
      }
    } catch { clearInterval(pollTimer); running.value = false }
  }, 800)
}

async function fetchResult(taskId) {
  try {
    const res  = await fetch(`/api/backtest/result/${taskId}`)
    const data = await res.json()
    if (data.status === 'done') resultHtml.value = data.html
    else runError.value = data.error || '获取结果失败'
  } finally {
    running.value = false
  }
}

onMounted(fetchList)
</script>

<style scoped>
/* ── 页面容器 ── */
.page-body {
  max-width: 880px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-5) var(--space-10);
  position: relative;
}

/* ── 页头 ── */
.page-header {
  margin-bottom: var(--space-5);
}

.page-title {
  font-size: var(--size-title3);
  font-weight: 600;
  color: var(--label);
  letter-spacing: var(--tracking-tight);
}

/* ── 策略卡片网格 ── */
.proj-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--space-4);
}

/* ── 策略卡片（Apple 卡片样式） ── */
.proj-card {
  background: var(--bg-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  padding: var(--space-4);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  transition: box-shadow .15s;
}
.proj-card:hover { box-shadow: var(--shadow-sm); }

.proj-meta { flex: 1; }

.proj-name {
  font-size: var(--size-body);
  font-weight: 600;
  color: var(--label);
  margin-bottom: 4px;
  letter-spacing: var(--tracking-body);
}

.proj-file {
  font-size: var(--size-xs);
  color: var(--label-muted);
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
}

/* ── 运行按钮（Apple 主操作风格） ── */
.run-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  height: 32px;
  border-radius: var(--radius-sm);
  border: none;
  background: var(--accent);
  color: #ffffff;
  font-size: var(--size-sm);
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  letter-spacing: var(--tracking-small);
  transition: background .15s, opacity .15s;
}
.run-btn:hover { background: var(--accent-hover); }
.run-btn--disabled { opacity: 0.4; cursor: not-allowed; }

.empty {
  color: var(--label-muted);
  font-size: var(--size-sm);
  text-align: center;
  padding: var(--space-10) 0;
}

/* ── 运行蒙层（Apple alert / sheet 风格） ── */
.overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.35);
  backdrop-filter: blur(8px) saturate(1.6);
  -webkit-backdrop-filter: blur(8px) saturate(1.6);
  z-index: 99999;
  display: flex;
  align-items: center;
  justify-content: center;
}

.overlay-card {
  background: rgba(255,255,255,0.94);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow);
  padding: var(--space-8) var(--space-10);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--space-3);
  min-width: 280px;
  text-align: center;
}

.overlay-name {
  font-size: var(--size-headline);
  font-weight: 600;
  color: var(--label);
  letter-spacing: var(--tracking-tight);
}

.overlay-sub {
  font-size: var(--size-sm);
  color: var(--label-muted);
  margin-top: -8px;
}

.progress-track {
  width: 240px;
  height: 4px;
  background: var(--gray-5);
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width .3s ease;
}

.overlay-pct {
  font-size: var(--size-sm);
  color: var(--label-muted);
  font-variant-numeric: tabular-nums;
}

.overlay-error {
  font-size: var(--size-sm);
  color: var(--red);
  max-width: 320px;
}

/* ── 结果栏 ── */
.result-bar {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-4);
}

.result-title {
  font-size: var(--size-sm);
  color: var(--label-muted);
}

/* ── 结果 iframe ── */
.result-frame {
  width: 100%;
  height: calc(100vh - 140px);
  border: none;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
}
</style>
