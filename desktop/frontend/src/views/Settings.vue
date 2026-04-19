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

        <div class="field-row field-row--top">
          <div class="field-label">模型预设</div>
          <div class="field-control">
            <div class="vrm-preset-grid">
              <button
                v-for="p in VRM_PRESETS"
                :key="p.id"
                class="vrm-preset-btn"
                :class="{ active: form.vrmPreset === p.id }"
                @click="selectVrmPreset(p.id)"
                :title="p.desc"
              >
                <span class="vrm-preset-icon">{{ p.icon }}</span>
                <span class="vrm-preset-name">{{ p.label }}</span>
              </button>
            </div>
          </div>
        </div>

        <div class="field-row">
          <div class="field-label">场景主题</div>
          <div class="field-control">
            <select v-model="form.scenePreset" class="select-input">
              <option v-for="s in SCENE_PRESETS" :key="s.id" :value="s.id">{{ s.label }}</option>
            </select>
            <div class="field-hint">
              <span v-if="form.scenePreset === 'auto'">
                自动：官方示例使用深色空间，VRoid 素体使用明亮空间。
              </span>
              <span v-else-if="form.scenePreset === 'dark'">深邃星空背景，适合科技感形象。</span>
              <span v-else>纯白明亮背景，更适合展示角色肤色与服装。</span>
            </div>
          </div>
        </div>

        <template v-if="form.vrmPreset === 'custom'">
          <div class="field-row">
            <div class="field-label">VRM 链接</div>
            <div class="field-control">
              <input
                type="text"
                v-model="form.vrmUrl"
                placeholder="https://..."
                class="text-input"
              />
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
        </template>
        <div v-else class="field-row">
          <div class="field-label"></div>
          <div class="field-control">
            <div class="field-hint">
              {{ VRM_PRESETS.find(p => p.id === form.vrmPreset)?.desc }}
            </div>
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

      <!-- TTS 语音设置 -->
      <div class="card settings-card">
        <div class="card-section-title">语音朗读</div>

        <div class="field-row">
          <div class="field-label">启用 TTS</div>
          <div class="field-control">
            <label class="switch-label">
              <input type="checkbox" v-model="form.ttsEnabled" class="switch-input" />
              <span class="switch-slider" />
            </label>
            <div class="field-hint">助理回复完成后自动朗读内容（Edge TTS）</div>
          </div>
        </div>

        <template v-if="form.ttsEnabled">
          <div class="field-row">
            <div class="field-label">语音角色</div>
            <div class="field-control">
              <select v-model="form.ttsVoice" class="select-input">
                <option v-for="v in edgeVoices" :key="v.voice" :value="v.voice">
                  {{ v.name }} — {{ v.desc }}
                </option>
              </select>
            </div>
          </div>

          <div class="field-row">
            <div class="field-label">语速</div>
            <div class="field-control">
              <select v-model="form.ttsRate" class="select-input">
                <option value="-50%">慢</option>
                <option value="-20%">稍慢</option>
                <option value="+0%">正常</option>
                <option value="+20%">稍快</option>
                <option value="+50%">快</option>
              </select>
            </div>
          </div>

          <div class="field-row">
            <div class="field-label"></div>
            <div class="field-control">
              <button class="btn" @click="testTTS">试听</button>
            </div>
          </div>
        </template>
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import {
  STORAGE_KEY, PROVIDER_DEFAULTS, edgeVoices,
  VRM_PRESETS, SCENE_PRESETS,
  saveSettings as saveSettingsToStore,
  resolveUrl,
} from '@/composables/useSettings.js'

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
  vrmPreset: 'avatar_b',   // official | vroid_base | avatar_b | glb_custom | custom
  scenePreset: 'auto',     // auto | dark | light
  ttsEnabled: true,
  ttsVoice: 'zh-CN-XiaoxiaoNeural',
  ttsRate: '+0%',
  ttsPitch: '+0Hz',
  ttsVoiceUri: '',
  vrmUrl: '',
})

// VRM_PRESETS / SCENE_PRESETS 已从 useSettings.js 导入

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
// PROVIDER_DEFAULTS 已从 useSettings.js 导入

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
      const defaultUrl = PROVIDER_DEFAULTS[form.provider]?.apiUrl || 'https://api.openai.com/v1'
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

function selectVrmPreset(id) {
  form.vrmPreset = id
  if (id === 'avatar_b') {
    form.scenePreset = 'light'
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
  saveSettingsToStore({
    vrmPreset: form.vrmPreset,
    vrmPresetUserSet: true,   // 标记为用户主动选择
    scenePreset: form.scenePreset,
    vrmUrl: form.vrmUrl,
  })
  vrmSaveStatus.value = '已保存，切换到助理页面生效'
  setTimeout(() => { vrmSaveStatus.value = '' }, 3000)
}

// edgeVoices 已从 useSettings.js 导入

async function testTTS() {
  try {
    const res = await fetch('/api/tts/speech', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({
        text: '你好，我是助理小姐',
        voice: form.ttsVoice,
        rate: form.ttsRate,
        pitch: form.ttsPitch,
      }),
    })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    const blob = await res.blob()
    const audio = new Audio(URL.createObjectURL(blob))
    await audio.play()
  } catch (e) {
    // fallback: 浏览器原生 TTS
    if (window.speechSynthesis) {
      const u = new SpeechSynthesisUtterance('你好，我是助理小姐')
      u.lang = 'zh-CN'
      window.speechSynthesis.speak(u)
    }
  }
}

function saveSettings() {
  // 只保存 API/对话相关字段，VRM/场景设置由 saveVrmSettings 单独管理
  saveSettingsToStore({
    provider:     form.provider,
    apiKey:       form.apiKey,
    apiUrl:       form.apiUrl,
    model:        form.model,
    systemPrompt: form.systemPrompt,
    ttsEnabled:   form.ttsEnabled,
    ttsVoice:     form.ttsVoice,
    ttsRate:      form.ttsRate,
    ttsPitch:     form.ttsPitch,
    ttsVoiceUri: form.ttsVoiceUri,
  })
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
  // Edge TTS 语音列表由后端提供，无需浏览器加载
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

.vrm-preset-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--space-2);
}
.vrm-preset-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: var(--space-2) var(--space-1);
  border: 1px solid var(--separator-opaque);
  border-radius: var(--radius);
  background: var(--bg-secondary);
  cursor: pointer;
  transition: all 0.15s;
  font-family: inherit;
}
.vrm-preset-btn:hover {
  border-color: var(--accent);
  background: rgba(0, 122, 255, 0.05);
}
.vrm-preset-btn.active {
  border-color: var(--accent);
  background: rgba(0, 122, 255, 0.08);
}
.vrm-preset-icon { font-size: 20px; }
.vrm-preset-name {
  font-size: var(--size-xs);
  color: var(--label-2);
  font-weight: 500;
}
.vrm-preset-btn.active .vrm-preset-name { color: var(--accent); }

.vrm-file-name {
  margin-left: 10px; font-size: var(--size-xs);
  color: var(--label-muted); font-family: 'SF Mono', Menlo, monospace;
}

/* Switch */
.switch-label {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  cursor: pointer;
}
.switch-input {
  opacity: 0;
  width: 0;
  height: 0;
}
.switch-slider {
  position: absolute;
  inset: 0;
  background: var(--separator-opaque);
  border-radius: 24px;
  transition: .2s;
}
.switch-slider::before {
  content: "";
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: white;
  border-radius: 50%;
  transition: .2s;
}
.switch-input:checked + .switch-slider {
  background: var(--accent);
}
.switch-input:checked + .switch-slider::before {
  transform: translateX(20px);
}
</style>
