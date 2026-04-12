<template>
  <div class="page-body">
    <div class="page-header">
      <h1 class="page-title">数据管理</h1>
      <p class="page-sub">选择数据表后点击"增量下载"，自动拉取新增数据（首次运行将下载全部历史）</p>
    </div>

    <!-- 加载中 -->
    <div v-if="loadingTables" class="loading-mask" style="height:200px;">
      <div class="spinner"></div>
    </div>

    <!-- 表格列表 -->
    <template v-else>
      <!-- 分组 -->
      <div v-for="category in categories" :key="category" class="category-section">
        <div class="category-header">
          <label class="cat-checkbox">
            <input
              type="checkbox"
              :checked="isCategoryChecked(category)"
              :indeterminate.prop="isCategoryIndeterminate(category)"
              @change="toggleCategory(category, $event.target.checked)"
            />
            <span class="cat-label">{{ category }}</span>
          </label>
          <span class="cat-count">{{ tablesByCategory(category).length }} 张表</span>
        </div>

        <div class="table-list">
          <div
            v-for="t in tablesByCategory(category)"
            :key="t.id"
            class="table-row"
            :class="{ 'table-row--selected': selected.has(t.id) }"
            @click="toggleRow(t.id)"
          >
            <div class="row-check">
              <input
                type="checkbox"
                :checked="selected.has(t.id)"
                @click.stop
                @change="toggleRow(t.id)"
              />
            </div>
            <div class="row-main">
              <div class="row-label">{{ t.label }}</div>
              <div class="row-desc">{{ t.description }}</div>
            </div>
            <div class="row-meta">
              <div class="meta-item">
                <span class="meta-key">上次更新</span>
                <span class="meta-val">{{ t.last_update || '—' }}</span>
              </div>
              <div class="meta-item">
                <span class="meta-key">行数</span>
                <span class="meta-val">{{ formatCount(t.row_count) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 底部操作栏 -->
      <div class="action-bar">
        <div class="action-left">
          <button class="btn btn-ghost" @click="selectAll">全选</button>
          <button class="btn btn-ghost" @click="selectNone">全不选</button>
          <span class="selected-hint">已选 {{ selected.size }} 张</span>
        </div>
        <button
          class="btn btn-primary"
          :class="{ 'btn--disabled': selected.size === 0 || running }"
          :disabled="selected.size === 0 || running"
          @click="startDownload"
        >
          <svg v-if="!running" width="12" height="12" viewBox="0 0 12 12" fill="currentColor" style="margin-right:5px">
            <path d="M6 1v7M3 6l3 3 3-3M1 10h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
          </svg>
          <div v-else class="btn-spinner"></div>
          {{ running ? '下载中…' : '增量下载' }}
        </button>
      </div>

      <!-- 进度日志 -->
      <div v-if="taskId" class="log-panel">
        <div class="log-header">
          <span class="log-title">下载日志</span>
          <span v-if="taskStatus === 'running'" class="log-status log-status--running">进行中 {{ Math.round(taskProgress * 100) }}%</span>
          <span v-else-if="taskStatus === 'done'" class="log-status log-status--done">完成</span>
          <span v-else-if="taskStatus === 'error'" class="log-status log-status--error">出错</span>
        </div>
        <div v-if="taskStatus === 'running'" class="progress-track">
          <div class="progress-fill" :style="{ width: Math.round(taskProgress * 100) + '%' }"></div>
        </div>
        <div v-if="currentTable" class="log-current">正在处理：{{ currentTable }}</div>
        <div class="log-body" ref="logBodyRef">
          <div v-for="(line, i) in logLines" :key="i" class="log-line">{{ line }}</div>
        </div>
        <button v-if="taskStatus !== 'running'" class="btn btn-ghost" style="margin-top:12px" @click="refreshTables">刷新表状态</button>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted } from 'vue'

const tables        = ref([])
const loadingTables = ref(true)
const selected      = ref(new Set())
const running       = ref(false)
const taskId        = ref(null)
const taskStatus    = ref('')
const taskProgress  = ref(0)
const currentTable  = ref('')
const logLines      = ref([])
const logBodyRef    = ref(null)

let pollTimer = null

// ── 分组 ────────────────────────────────────────────────────────────────────

const categories = computed(() => {
  const seen = new Set()
  const order = []
  for (const t of tables.value) {
    if (!seen.has(t.category)) { seen.add(t.category); order.push(t.category) }
  }
  return order
})

function tablesByCategory(cat) {
  return tables.value.filter(t => t.category === cat)
}

function isCategoryChecked(cat) {
  const rows = tablesByCategory(cat)
  return rows.length > 0 && rows.every(t => selected.value.has(t.id))
}

function isCategoryIndeterminate(cat) {
  const rows = tablesByCategory(cat)
  const cnt  = rows.filter(t => selected.value.has(t.id)).length
  return cnt > 0 && cnt < rows.length
}

function toggleCategory(cat, checked) {
  const rows = tablesByCategory(cat)
  const next = new Set(selected.value)
  rows.forEach(t => checked ? next.add(t.id) : next.delete(t.id))
  selected.value = next
}

function toggleRow(id) {
  const next = new Set(selected.value)
  next.has(id) ? next.delete(id) : next.add(id)
  selected.value = next
}

function selectAll()  { selected.value = new Set(tables.value.map(t => t.id)) }
function selectNone() { selected.value = new Set() }

// ── 格式化 ──────────────────────────────────────────────────────────────────

function formatCount(n) {
  if (n < 0) return '—'
  if (n === 0) return '空表'
  if (n >= 1e8) return (n / 1e8).toFixed(1) + ' 亿'
  if (n >= 1e4) return (n / 1e4).toFixed(1) + ' 万'
  return n.toLocaleString()
}

// ── 数据加载 ────────────────────────────────────────────────────────────────

async function fetchTables() {
  loadingTables.value = true
  try {
    const res  = await fetch('/api/download/tables')
    const data = await res.json()
    tables.value = data.tables || []
  } catch (e) {
    console.error('获取表列表失败', e)
  } finally {
    loadingTables.value = false
  }
}

async function refreshTables() {
  await fetchTables()
}

// ── 下载 ─────────────────────────────────────────────────────────────────────

async function startDownload() {
  if (selected.value.size === 0 || running.value) return
  running.value    = true
  taskStatus.value = 'running'
  taskProgress.value = 0
  currentTable.value = ''
  logLines.value   = []

  try {
    const res  = await fetch('/api/download/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ tables: [...selected.value] }),
    })
    const data = await res.json()
    if (data.error) throw new Error(data.error)
    taskId.value = data.task_id
    pollStatus(data.task_id)
  } catch (e) {
    logLines.value.push(`启动失败：${e.message}`)
    taskStatus.value = 'error'
    running.value    = false
  }
}

function pollStatus(id) {
  pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`/api/download/status/${id}`)
      const data = await res.json()
      taskProgress.value = data.progress || 0
      currentTable.value = data.current  || ''
      logLines.value     = data.log      || []
      taskStatus.value   = data.status

      // 自动滚动日志
      nextTick(() => {
        if (logBodyRef.value) logBodyRef.value.scrollTop = logBodyRef.value.scrollHeight
      })

      if (data.status === 'done' || data.status === 'error') {
        clearInterval(pollTimer)
        pollTimer    = null
        running.value = false
      }
    } catch {
      clearInterval(pollTimer)
      pollTimer    = null
      running.value = false
    }
  }, 1000)
}

onMounted(fetchTables)
onUnmounted(() => { if (pollTimer) clearInterval(pollTimer) })
</script>

<style scoped>
.page-body {
  max-width: 960px;
  margin: 0 auto;
  padding: var(--space-8) var(--space-5) var(--space-10);
}

.page-header { margin-bottom: var(--space-6); }

.page-title {
  font-size: var(--size-title3);
  font-weight: 600;
  color: var(--label);
  letter-spacing: var(--tracking-tight);
  margin-bottom: var(--space-1);
}

.page-sub {
  font-size: var(--size-sm);
  color: var(--label-muted);
}

/* ── 分组 ── */
.category-section { margin-bottom: var(--space-4); }

.category-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 32px;
  padding: 0 var(--space-3);
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
}

.cat-checkbox {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
}

.cat-label {
  font-size: var(--size-sm);
  font-weight: 600;
  color: var(--label);
}

.cat-count {
  font-size: var(--size-xs);
  color: var(--label-muted);
}

/* ── 表格行 ── */
.table-list {
  background: var(--bg-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
}

.table-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  height: 32px;
  padding: 0 var(--space-4);
  cursor: pointer;
  border-bottom: 1px solid var(--separator);
  transition: background .12s;
}
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--bg-secondary); }
.table-row--selected { background: rgba(0, 122, 255, 0.04); }

.row-check { flex-shrink: 0; }
.row-check input { cursor: pointer; width: 15px; height: 15px; }

.row-main { flex: 1; min-width: 0; }

.row-label {
  font-size: var(--size-sm);
  font-weight: 500;
  color: var(--label);
  line-height: 1.2;
}

.row-desc {
  font-size: 11px;
  color: var(--label-muted);
  margin-top: 2px;
  line-height: 1.2;
}

.row-meta {
  display: flex;
  gap: var(--space-5);
  flex-shrink: 0;
}

.meta-item {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 1px;
  min-width: 80px;
}

.meta-key {
  font-size: 10px;
  color: var(--label-muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.meta-val {
  font-size: var(--size-sm);
  color: var(--label);
  font-variant-numeric: tabular-nums;
}

/* ── 操作栏 ── */
.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-4) 0;
  border-top: 1px solid var(--separator);
  margin-top: var(--space-2);
  position: sticky;
  bottom: 0;
  background: var(--bg-base);
}

.action-left {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.selected-hint {
  font-size: var(--size-sm);
  color: var(--label-muted);
  margin-left: var(--space-1);
}

.btn { display: inline-flex; align-items: center; }

.btn-ghost {
  height: 30px;
  padding: 0 var(--space-3);
  border-radius: var(--radius-sm);
  border: 1px solid var(--separator);
  background: transparent;
  font-size: var(--size-sm);
  font-family: inherit;
  color: var(--label-secondary);
  cursor: pointer;
  transition: background .12s;
}
.btn-ghost:hover { background: var(--bg-secondary); }

.btn-primary {
  height: 32px;
  padding: 0 var(--space-4);
  border-radius: var(--radius-sm);
  border: none;
  background: var(--accent);
  color: #fff;
  font-size: var(--size-sm);
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  transition: background .12s, opacity .12s;
  gap: 0;
}
.btn-primary:hover { background: var(--accent-hover); }
.btn--disabled { opacity: 0.4; cursor: not-allowed !important; }

.btn-spinner {
  width: 12px;
  height: 12px;
  border: 1.5px solid rgba(255,255,255,0.35);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin-right: 5px;
}

/* ── 日志面板 ── */
.log-panel {
  margin-top: var(--space-5);
  background: var(--bg-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  padding: var(--space-4);
}

.log-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: var(--space-3);
}

.log-title {
  font-size: var(--size-sm);
  font-weight: 600;
  color: var(--label);
}

.log-status {
  font-size: var(--size-xs);
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 10px;
}
.log-status--running { background: rgba(0,122,255,0.12); color: var(--accent); }
.log-status--done    { background: rgba(52,199,89,0.12);  color: #34c759; }
.log-status--error   { background: rgba(255,59,48,0.12);  color: var(--red); }

.progress-track {
  height: 3px;
  background: var(--gray-5);
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: var(--space-2);
}
.progress-fill {
  height: 100%;
  background: var(--accent);
  border-radius: 2px;
  transition: width .4s ease;
}

.log-current {
  font-size: var(--size-xs);
  color: var(--accent);
  margin-bottom: var(--space-2);
}

.log-body {
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: var(--space-3);
  max-height: 200px;
  overflow-y: auto;
  font-family: 'SF Mono', 'Menlo', 'Monaco', 'Consolas', monospace;
  font-size: 11px;
  color: var(--label-secondary);
}

.log-line {
  line-height: 1.4;
  white-space: pre-wrap;
  word-break: break-all;
  padding: 2px 0;
}

@keyframes spin { to { transform: rotate(360deg); } }

/* ── 深色模式 ── */
@media (prefers-color-scheme: dark) {
  .table-row--selected { background: rgba(10, 132, 255, 0.08); }
}
</style>
