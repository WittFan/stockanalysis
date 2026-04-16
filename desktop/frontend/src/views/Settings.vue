<template>
  <div class="settings-page">
    <div class="settings-container">
      <div class="page-header">
        <h1 class="page-title">设置</h1>
        <p class="page-subtitle">配置大模型接口，让助理小姐更聪明</p>
      </div>

      <div class="card settings-card">
        <div class="card-section-title">大模型接口</div>

        <div class="field-row">
          <div class="field-label">API 提供商</div>
          <div class="field-control">
            <select v-model="form.provider" class="select-input" @change="onProviderChange">
              <option value="openai">OpenAI / 兼容接口（推荐）</option>
              <option value="kimi">Kimi Code（月之暗面）</option>
              <option value="anthropic">Anthropic Claude</option>
              <option value="local_kimi">本地 Kimi CLI（无需 API Key）</option>
            </select>
            <div v-if="form.provider === 'local_kimi'" class="field-hint local-hint">
              <span v-if="kimiCliStatus === null">检测中...</span>
              <span v-else-if="kimiCliStatus" class="hint-ok">✓ 已检测到 kimi CLI：{{ kimiCliPath }}</span>
              <span v-else class="hint-err">
                ✗ 未找到 kimi CLI，请先安装：
                <code>curl -LsSf https://code.kimi.com/install.sh | bash</code>
                然后运行 <code>kimi login</code> 完成认证
              </span>
            </div>
          </div>
        </div>

        <template v-if="form.provider !== 'local_kimi'">
          <div class="field-row">
            <div class="field-label">API Key</div>
            <div class="field-control">
              <input
                type="password"
                v-model="form.apiKey"
                :placeholder="form.provider === 'anthropic' ? 'sk-ant-...' : 'sk-...'"
                class="text-input"
                autocomplete="off"
              />
            </div>
          </div>

          <div class="field-row">
            <div class="field-label">API 地址</div>
            <div class="field-control">
              <input
                type="text"
                v-model="form.apiUrl"
                :placeholder="form.provider === 'anthropic' ? 'https://api.anthropic.com' : 'https://api.openai.com/v1'"
                class="text-input"
              />
              <div class="field-hint">可填写自托管或代理地址</div>
            </div>
          </div>

          <div class="field-row">
            <div class="field-label">模型</div>
            <div class="field-control">
              <input
                type="text"
                v-model="form.model"
                :placeholder="form.provider === 'anthropic' ? 'claude-opus-4-6' : 'gpt-4o'"
                class="text-input"
              />
            </div>
          </div>
        </template>

        <div class="field-row field-row--top">
          <div class="field-label">系统提示词</div>
          <div class="field-control">
            <textarea
              v-model="form.systemPrompt"
              rows="5"
              class="textarea-input"
              placeholder="描述助理的性格与专长..."
            ></textarea>
          </div>
        </div>

        <div class="action-row">
          <div class="action-left">
            <span v-if="saveStatus === 'saved'" class="status-saved">已保存</span>
            <span v-if="testResult" class="status-test" :class="testResult.ok ? 'ok' : 'fail'">
              {{ testResult.message }}
            </span>
          </div>
          <div class="action-buttons">
            <button v-if="form.provider !== 'local_kimi'" class="btn" @click="testConnection" :disabled="isTesting">
              {{ isTesting ? '测试中...' : '测试连接' }}
            </button>
            <button v-else class="btn" @click="checkKimiCli" :disabled="isTesting">
              {{ isTesting ? '检测中...' : '检测 kimi CLI' }}
            </button>
            <button class="btn btn-primary" @click="saveSettings">保存</button>
          </div>
        </div>
      </div>

      <!-- VRM 模型配置 -->
      <div class="card settings-card">
        <div class="card-section-title">虚拟形象</div>

        <div class="field-row">
          <div class="field-label">VRM 模型</div>
          <div class="field-control">
            <input
              type="text"
              v-model="form.vrmUrl"
              placeholder="https://... 或留空使用内置示例模型"
              class="text-input"
            />
            <div class="field-hint">
              支持远程 URL 或本地文件路径。当前已内置
              <strong>VRoid Studio 女性素体</strong>
              （含 52 BlendShapes），留空即可使用。也可从
              <a href="https://hub.vroid.com" target="_blank" class="field-link">VRoid Hub</a>
              下载其他免费 VRM 角色，粘贴直链或选择本地文件。
            </div>
          </div>
        </div>

        <div class="field-row">
          <div class="field-label">本地文件</div>
          <div class="field-control">
            <label class="file-btn">
              <input type="file" accept=".vrm" style="display:none" @change="onVrmFile" />
              📂 选择 .vrm 文件
            </label>
            <span v-if="vrmFileName" class="vrm-file-name">{{ vrmFileName }}</span>
          </div>
        </div>

        <div class="action-row">
          <div class="action-left">
            <span v-if="vrmSaveStatus" class="status-saved">{{ vrmSaveStatus }}</span>
          </div>
          <div class="action-buttons">
            <button class="btn btn-primary" @click="saveVrmSettings">应用</button>
          </div>
        </div>
      </div>

      <div class="card settings-card">
        <div class="card-section-title">助理性格</div>
        <div class="preset-grid">
          <button
            v-for="preset in presets"
            :key="preset.id"
            class="preset-btn"
            :class="{ active: selectedPreset === preset.id }"
            @click="applyPreset(preset)"
          >
            <span class="preset-icon">{{ preset.icon }}</span>
            <span class="preset-name">{{ preset.name }}</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'

const STORAGE_KEY = 'assistant_settings'

const DEFAULT_SYSTEM_PROMPT = `你是助理小姐，一位温柔、聪明、可爱的AI助理。你有着美丽的外表和善解人意的性格。
你喜欢用简洁友好的语言与用户交流，偶尔会用一些可爱的语气词。
你精通量化投资、股票分析、数学和编程，可以帮助用户解答各种问题。
请用中文回复，语气要温柔亲切。`

const form = reactive({
  provider: 'openai',
  apiKey: '',
  apiUrl: 'https://api.openai.com/v1',
  model: 'gpt-4o',
  systemPrompt: DEFAULT_SYSTEM_PROMPT,
  vrmUrl: '',
})

const isTesting = ref(false)
const testResult = ref(null)
const saveStatus = ref('')
const selectedPreset = ref('cute')
const vrmFileName  = ref('')
const vrmSaveStatus = ref('')
const kimiCliStatus = ref(null)   // null=未检测, true=可用, false=不可用
const kimiCliPath = ref('')

const presets = [
  {
    id: 'cute',
    icon: '🌸',
    name: '可爱温柔',
    prompt: `你是助理小姐，一位温柔、聪明、可爱的AI助理。你喜欢用简洁友好的语言与用户交流，偶尔会用一些可爱的语气词（如"呢""哦""嗯嗯"）。你精通量化投资、股票分析、数学和编程，可以帮助用户解答各种问题。请用中文回复，语气要温柔亲切。`,
  },
  {
    id: 'professional',
    icon: '💼',
    name: '专业干练',
    prompt: `你是一位专业的量化投研助理，拥有深厚的金融和编程知识。你的回答简洁、精准、有条理，不废话，直接给出结论和建议。请用中文回复。`,
  },
  {
    id: 'cheerful',
    icon: '✨',
    name: '活泼开朗',
    prompt: `你是助理小姐，一位活泼开朗、充满活力的AI助理！你说话很有感染力，喜欢用感叹号和emoji表达情绪。你热爱学习，对量化投资和编程充满热情，总能给用户带来积极的能量！请用中文回复。`,
  },
  {
    id: 'scholar',
    icon: '📚',
    name: '博学睿智',
    prompt: `你是一位博学的量化投研顾问，精通数学、统计学、金融理论和计算机科学。你喜欢深入分析问题，引经据典，提供有深度的见解。你的表达严谨而不失亲和力。请用中文回复。`,
  },
]

// 各提供商默认配置
const PROVIDER_DEFAULTS = {
  openai:     { apiUrl: 'https://api.openai.com/v1',      model: 'gpt-4o' },
  kimi:       { apiUrl: 'https://api.kimi.com/coding/v1', model: 'kimi-for-coding' },
  anthropic:  { apiUrl: 'https://api.anthropic.com',      model: 'claude-opus-4-6' },
  local_kimi: { apiUrl: '', model: '' },
}

function onProviderChange() {
  const defaults = PROVIDER_DEFAULTS[form.provider]
  if (defaults) {
    form.apiUrl = defaults.apiUrl
    form.model  = defaults.model
  }
  testResult.value = null
  if (form.provider === 'local_kimi') {
    checkKimiCli()
  }
}

async function checkKimiCli() {
  isTesting.value = true
  kimiCliStatus.value = null
  try {
    const res = await fetch('/api/assistant/status')
    const data = await res.json()
    kimiCliStatus.value = data.kimi_available
    kimiCliPath.value = data.kimi_path || ''
    testResult.value = data.kimi_available
      ? { ok: true, message: `kimi CLI 已就绪：${data.kimi_path}` }
      : { ok: false, message: '未找到 kimi CLI，请先安装并运行 kimi login' }
  } catch (e) {
    kimiCliStatus.value = false
    testResult.value = { ok: false, message: `检测失败：${e.message}` }
  } finally {
    isTesting.value = false
  }
}

function applyPreset(preset) {
  selectedPreset.value = preset.id
  form.systemPrompt = preset.prompt
}

async function testConnection() {
  if (!form.apiKey) {
    testResult.value = { ok: false, message: '请先填写 API Key' }
    return
  }
  isTesting.value = true
  testResult.value = null

  // 开发模式走 Vite 代理，Electron/生产直连
  const PROXY_MAP = {
    'https://api.openai.com/v1':  '/proxy/openai/v1',
    'https://api.kimi.com/coding/v1': '/proxy/kimi/coding/v1',
    'https://api.anthropic.com':  '/proxy/anthropic',
  }
  const isDev = import.meta.env.DEV && !window.electronAPI?.isElectron
  const resolveUrl = (url) => isDev && PROXY_MAP[url] ? PROXY_MAP[url] : url

  try {
    if (form.provider === 'anthropic') {
      // Anthropic 原生格式
      const baseUrl = resolveUrl(form.apiUrl || 'https://api.anthropic.com')
      const res = await fetch(`${baseUrl}/v1/messages`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          'x-api-key': form.apiKey,
          'anthropic-version': '2023-06-01',
        },
        body: JSON.stringify({
          model: form.model || 'claude-haiku-4-5-20251001',
          max_tokens: 10,
          messages: [{ role: 'user', content: 'hi' }],
        }),
      })
      if (res.ok) {
        testResult.value = { ok: true, message: '连接成功！' }
      } else {
        const err = await res.json().catch(() => ({}))
        testResult.value = { ok: false, message: `连接失败: ${err?.error?.message || res.status}` }
      }
    } else {
      // OpenAI 兼容格式（OpenAI / Kimi Code / 其他）
      const defaultUrl = form.provider === 'kimi' ? 'https://api.kimi.com/coding/v1' : 'https://api.openai.com/v1'
      const baseUrl = resolveUrl(form.apiUrl || defaultUrl)
      const extraHeaders = form.provider === 'kimi' ? { 'user-agent': 'kimi-cli/1.0.0' } : {}
      const res = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: {
          'content-type': 'application/json',
          authorization: `Bearer ${form.apiKey}`,
          ...extraHeaders,
        },
        body: JSON.stringify({
          model: form.model || (form.provider === 'kimi' ? 'kimi-for-coding' : 'gpt-4o'),
          max_tokens: 10,
          messages: [{ role: 'user', content: 'hi' }],
        }),
      })
      if (res.ok) {
        testResult.value = { ok: true, message: '连接成功！' }
      } else {
        const err = await res.json().catch(() => ({}))
        testResult.value = { ok: false, message: `连接失败: ${err?.error?.message || res.status}` }
      }
    }
  } catch (e) {
    testResult.value = { ok: false, message: `网络错误: ${e.message}` }
  } finally {
    isTesting.value = false
  }
}

function onVrmFile(e) {
  const file = e.target.files?.[0]
  if (!file) return
  vrmFileName.value = file.name
  // 生成 Object URL 供 Three.js 加载本地文件
  const objectUrl = URL.createObjectURL(file)
  form.vrmUrl = objectUrl
}

function saveVrmSettings() {
  const data = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}')
  data.vrmUrl = form.vrmUrl
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  vrmSaveStatus.value = '已保存，切换到助理页面生效'
  setTimeout(() => { vrmSaveStatus.value = '' }, 3000)
}

function saveSettings() {
  const data = { ...form }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  saveStatus.value = 'saved'
  setTimeout(() => { saveStatus.value = '' }, 2000)
}

onMounted(() => {
  const saved = localStorage.getItem(STORAGE_KEY)
  if (saved) {
    try {
      const data = JSON.parse(saved)
      Object.assign(form, data)
    } catch {}
  }
})
</script>

<style scoped>
.settings-page {
  min-height: calc(100vh - 44px);
  background: var(--bg-secondary);
  padding: var(--space-5) var(--space-5) var(--space-10);
}

.settings-container {
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: var(--space-6);
}

.page-title {
  font-size: var(--size-large);
  font-weight: 700;
  letter-spacing: var(--tracking-tight);
  color: var(--label);
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: var(--size-body);
  color: var(--label-2);
  margin: 0;
}

.settings-card {
  margin-bottom: var(--space-4);
  padding: var(--space-4);
}

.card-section-title {
  font-size: var(--size-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--label-muted);
  margin-bottom: var(--space-4);
}

.field-row {
  display: flex;
  align-items: center;
  gap: var(--space-4);
  margin-bottom: var(--space-3);
}

.field-row--top {
  align-items: flex-start;
}

.field-label {
  width: 90px;
  flex-shrink: 0;
  font-size: var(--size-body);
  color: var(--label-2);
  font-weight: 500;
}

.field-control {
  flex: 1;
  min-width: 0;
}

.field-hint {
  font-size: var(--size-xs);
  color: var(--label-muted);
  margin-top: 4px;
}

.select-input,
.text-input,
.textarea-input {
  width: 100%;
  box-sizing: border-box;
  background: var(--bg-secondary);
  border: 1px solid var(--separator-opaque);
  border-radius: var(--radius-sm);
  padding: 6px 10px;
  font-size: var(--size-body);
  color: var(--label);
  font-family: inherit;
  outline: none;
  transition: border-color 0.15s;
}

.select-input:focus,
.text-input:focus,
.textarea-input:focus {
  border-color: var(--accent);
}

.textarea-input {
  resize: vertical;
  line-height: var(--leading-body);
}

.action-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: var(--space-4);
  padding-top: var(--space-3);
  border-top: 0.5px solid var(--separator);
}

.action-left {
  font-size: var(--size-body);
}

.action-buttons {
  display: flex;
  gap: var(--space-2);
}

.status-saved {
  color: var(--green);
  font-weight: 500;
}

.status-test.ok {
  color: var(--green);
  font-weight: 500;
}

.status-test.fail {
  color: var(--red);
  font-weight: 500;
}

.preset-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--space-2);
}

.preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: var(--space-3) var(--space-2);
  border: 1px solid var(--separator-opaque);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}

.preset-btn:hover {
  border-color: var(--accent);
  background: rgba(0, 122, 255, 0.05);
}

.preset-btn.active {
  border-color: var(--accent);
  background: rgba(0, 122, 255, 0.08);
}

.preset-icon {
  font-size: 24px;
}

.preset-name {
  font-size: var(--size-xs);
  color: var(--label-2);
  font-weight: 500;
}

.preset-btn.active .preset-name {
  color: var(--accent);
}

.local-hint {
  margin-top: 6px;
  line-height: 1.6;
}
.local-hint code {
  background: var(--fill);
  padding: 1px 5px;
  border-radius: 4px;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 11px;
}
.hint-ok { color: var(--green); font-weight: 500; }
.hint-err { color: var(--red); }

.field-link {
  color: var(--accent);
  text-decoration: none;
}
.field-link:hover { text-decoration: underline; }

.file-btn {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 5px 14px; border-radius: var(--radius-sm);
  border: 1px solid var(--separator-opaque);
  background: var(--bg-secondary); color: var(--label-2);
  font-size: var(--size-body); cursor: pointer;
  font-family: inherit; transition: all .15s;
}
.file-btn:hover { border-color: var(--accent); color: var(--accent); }

.vrm-file-name {
  margin-left: 10px; font-size: var(--size-xs);
  color: var(--label-muted); font-family: 'SF Mono', Menlo, monospace;
}
</style>
