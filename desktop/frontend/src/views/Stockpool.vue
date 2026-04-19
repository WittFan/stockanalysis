<template>
  <div class="page-body">
    <div class="page-header">
      <h1 class="page-title">股票池管理</h1>
      <p class="page-sub">管理股票池标的，支持从 stockpool.xlsx 导入</p>
    </div>

    <!-- 工具栏：搜索 + 操作 -->
    <div class="toolbar">
      <div class="search-wrap">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <circle cx="7" cy="7" r="5.5"/><path d="M11 11l3.5 3.5" stroke-linecap="round"/>
        </svg>
        <input
          v-model="searchQ"
          class="search-input"
          placeholder="搜索股票代码或名称…"
          @input="onSearch"
        />
      </div>
      <div class="toolbar-actions">
        <button class="btn btn-ghost" :disabled="importing" @click="importXlsx">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          {{ importing ? '导入中…' : '从 xlsx 导入' }}
        </button>
        <button class="btn btn-primary" @click="openAdd">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          新增股票
        </button>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-mask" style="height:200px;">
      <div class="spinner"></div>
    </div>

    <!-- 空状态 -->
    <div v-else-if="!list.length" class="empty-state">
      <div style="font-size:36px;margin-bottom:12px">📋</div>
      <div class="empty-title">股票池为空</div>
      <div class="empty-sub">点击「从 xlsx 导入」或「新增股票」开始管理</div>
    </div>

    <!-- 数据表格 -->
    <div v-else class="data-table">
      <div class="table-header">
        <div class="th th-code">股票代码</div>
        <div class="th th-name">标的名称</div>
        <div class="th th-date">入池日期</div>
        <div class="th th-date">出池日期</div>
        <div class="th th-action">操作</div>
      </div>
      <div
        v-for="item in list"
        :key="item.id"
        class="table-row"
      >
        <div class="td td-code">{{ item.ts_code }}</div>
        <div class="td td-name">{{ item.name }}</div>
        <div class="td td-date">{{ item.in_date || '—' }}</div>
        <div class="td td-date">{{ item.out_date || '—' }}</div>
        <div class="td td-action">
          <button class="btn-icon" title="编辑" @click="openEdit(item)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/><path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
            </svg>
          </button>
          <button class="btn-icon btn-icon--danger" title="删除" @click="confirmDelete(item)">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6"/><line x1="10" y1="11" x2="10" y2="17"/><line x1="14" y1="11" x2="14" y2="17"/>
            </svg>
          </button>
        </div>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
        <div class="modal">
          <div class="modal-header">
            <h3 class="modal-title">{{ editingId ? '编辑股票' : '新增股票' }}</h3>
            <button class="modal-close" @click="closeModal">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
                <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
              </svg>
            </button>
          </div>
          <div class="modal-body">
            <div class="form-row">
              <label class="form-label">股票代码 <span class="required">*</span></label>
              <input v-model="form.ts_code" class="form-input" placeholder="如 600519.SH" />
            </div>
            <div class="form-row">
              <label class="form-label">标的名称 <span class="required">*</span></label>
              <input v-model="form.name" class="form-input" placeholder="如 贵州茅台" />
            </div>
            <div class="form-row">
              <label class="form-label">入池日期</label>
              <input v-model="form.in_date" type="date" class="form-input" />
            </div>
            <div class="form-row">
              <label class="form-label">出池日期</label>
              <input v-model="form.out_date" type="date" class="form-input" />
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn" @click="closeModal">取消</button>
            <button class="btn btn-primary" :disabled="saving" @click="save">
              {{ saving ? '保存中…' : '保存' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const list = ref([])
const loading = ref(false)
const searchQ = ref('')
const importing = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editingId = ref(null)

const form = ref({ ts_code: '', name: '', in_date: '', out_date: '' })

let searchTimer = null

async function fetchList() {
  loading.value = true
  try {
    const q = searchQ.value.trim()
    const url = q ? `/api/stockpool?q=${encodeURIComponent(q)}` : '/api/stockpool'
    const res = await fetch(url)
    const data = await res.json()
    list.value = data.data || []
  } catch (e) {
    console.error('获取股票池失败', e)
    list.value = []
  } finally {
    loading.value = false
  }
}

function onSearch() {
  clearTimeout(searchTimer)
  searchTimer = setTimeout(fetchList, 300)
}

async function importXlsx() {
  if (!confirm('将从 stockpool.xlsx 重新导入，现有数据将被覆盖，是否继续？')) return
  importing.value = true
  try {
    const res = await fetch('/api/stockpool/import', { method: 'POST' })
    const data = await res.json()
    if (res.ok) {
      alert(data.message)
      fetchList()
    } else {
      alert(data.error || '导入失败')
    }
  } catch (e) {
    alert('导入请求失败')
  } finally {
    importing.value = false
  }
}

function openAdd() {
  editingId.value = null
  form.value = { ts_code: '', name: '', in_date: '', out_date: '' }
  showModal.value = true
}

function openEdit(item) {
  editingId.value = item.id
  form.value = {
    ts_code: item.ts_code,
    name: item.name,
    in_date: item.in_date || '',
    out_date: item.out_date || '',
  }
  showModal.value = true
}

function closeModal() {
  showModal.value = false
}

async function save() {
  const body = {
    ts_code: form.value.ts_code.trim(),
    name: form.value.name.trim(),
    in_date: form.value.in_date || null,
    out_date: form.value.out_date || null,
  }
  if (!body.ts_code || !body.name) {
    alert('股票代码和名称不能为空')
    return
  }
  saving.value = true
  try {
    const url = editingId.value ? `/api/stockpool/${editingId.value}` : '/api/stockpool'
    const method = editingId.value ? 'PUT' : 'POST'
    const res = await fetch(url, {
      method,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })
    const data = await res.json()
    if (res.ok) {
      closeModal()
      fetchList()
    } else {
      alert(data.error || '保存失败')
    }
  } catch (e) {
    alert('保存请求失败')
  } finally {
    saving.value = false
  }
}

function confirmDelete(item) {
  if (!confirm(`确定删除 ${item.ts_code} ${item.name}？`)) return
  fetch(`/api/stockpool/${item.id}`, { method: 'DELETE' })
    .then(res => res.json())
    .then(() => fetchList())
    .catch(() => alert('删除失败'))
}

onMounted(fetchList)
</script>

<style scoped>
/* ── 工具栏 ── */
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  margin-bottom: var(--space-4);
}
.toolbar-actions {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

/* ── 搜索框 ── */
.search-wrap {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex: 1;
  max-width: 320px;
  background: var(--bg-secondary);
  border-radius: var(--radius-sm);
  padding: 0 var(--space-3);
  height: 32px;
  color: var(--label-muted);
}
.search-input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: var(--size-sm);
  color: var(--label);
  outline: none;
  font-family: inherit;
}
.search-input::placeholder { color: var(--label-muted); }

/* ── 数据表格 ── */
.data-table {
  background: var(--bg-primary);
  border-radius: var(--radius);
  box-shadow: var(--shadow-xs);
  overflow: hidden;
  font-size: var(--size-sm);
}
.table-header {
  display: flex;
  align-items: center;
  height: 32px;
  padding: 0 var(--space-4);
  background: var(--bg-secondary);
  border-bottom: 0.5px solid var(--separator-opaque);
  font-weight: 600;
  color: var(--label-2);
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}
.table-row {
  display: flex;
  align-items: center;
  height: 40px;
  padding: 0 var(--space-4);
  border-bottom: 0.5px solid var(--separator-opaque);
  transition: background .1s;
}
.table-row:last-child { border-bottom: none; }
.table-row:hover { background: var(--bg-secondary); }

.th, .td { display: flex; align-items: center; }
.th-code, .td-code { width: 120px; flex-shrink: 0; font-family: 'SF Mono', Menlo, monospace; }
.th-name, .td-name { flex: 1; min-width: 0; }
.th-date, .td-date { width: 110px; flex-shrink: 0; color: var(--label-2); }
.th-action, .td-action { width: 80px; flex-shrink: 0; justify-content: flex-end; gap: 4px; }

/* ── 图标按钮 ── */
.btn-icon {
  width: 26px;
  height: 26px;
  border: none;
  border-radius: var(--radius-sm);
  background: transparent;
  color: var(--label-muted);
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: all .12s;
}
.btn-icon:hover { background: var(--fill); color: var(--accent); }
.btn-icon--danger:hover { color: var(--red); }

/* ── 空状态 ── */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 48px 24px;
}
.empty-title { font-size: 15px; font-weight: 600; color: var(--label); margin-bottom: 5px; }
.empty-sub { font-size: 12px; color: var(--label-muted); }

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.35);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  backdrop-filter: blur(4px);
}
.modal {
  width: 400px;
  max-width: 90vw;
  background: var(--bg-primary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow);
  overflow: hidden;
}
.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 0.5px solid var(--separator-opaque);
}
.modal-title { font-size: var(--size-headline); font-weight: 600; margin: 0; }
.modal-close {
  width: 28px; height: 28px; border: none; border-radius: var(--radius-sm);
  background: transparent; color: var(--label-muted); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
}
.modal-close:hover { background: var(--fill); color: var(--label); }

.modal-body { padding: 16px; }
.form-row { margin-bottom: 14px; }
.form-row:last-child { margin-bottom: 0; }
.form-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--label-2);
  margin-bottom: 5px;
}
.required { color: var(--red); }
.form-input {
  width: 100%;
  height: 34px;
  padding: 0 10px;
  border: 1px solid var(--separator-opaque);
  border-radius: var(--radius-sm);
  background: var(--bg-secondary);
  font-size: var(--size-sm);
  font-family: inherit;
  color: var(--label);
  outline: none;
  box-sizing: border-box;
  transition: border-color .15s;
}
.form-input:focus { border-color: var(--accent); }

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--space-2);
  padding: 12px 16px;
  border-top: 0.5px solid var(--separator-opaque);
}

/* ── 过渡动画 ── */
.fade-enter-active, .fade-leave-active { transition: opacity .2s ease; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
