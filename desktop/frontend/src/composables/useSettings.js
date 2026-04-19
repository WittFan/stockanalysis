/**
 * 设置共享模块
 * 统一处理 localStorage 读写、Provider 配置、VRM/场景预设、TTS 语音等
 */

export const STORAGE_KEY = 'assistant_settings'

// ── API 提供商默认配置 ──────────────────────────────────────────────
export const PROVIDER_DEFAULTS = {
  openai:     { apiUrl: 'https://api.openai.com/v1',      model: 'gpt-4o' },
  kimi:       { apiUrl: 'https://api.kimi.com/coding/v1', model: 'kimi-for-coding' },
  anthropic:  { apiUrl: 'https://api.anthropic.com',      model: 'claude-opus-4-6' },
  local_kimi: { apiUrl: '', model: '' },
}

// ── 开发模式代理映射 ────────────────────────────────────────────────
const PROXY_MAP = {
  'https://api.openai.com/v1':       '/proxy/openai/v1',
  'https://api.kimi.com/coding/v1':  '/proxy/kimi/coding/v1',
  'https://api.anthropic.com':       '/proxy/anthropic',
}

export function resolveUrl(url) {
  const isDev = import.meta.env.DEV && !window.electronAPI?.isElectron
  return (isDev && PROXY_MAP[url]) ? PROXY_MAP[url] : url
}

// ── Edge TTS 语音列表 ───────────────────────────────────────────────
export const edgeVoices = [
  { voice: 'zh-CN-XiaoxiaoNeural', name: '晓晓', desc: '温柔女性（推荐）' },
  { voice: 'zh-CN-XiaoyiNeural',   name: '晓伊', desc: '活泼女性' },
  { voice: 'zh-CN-YunjianNeural',  name: '云健', desc: '成熟男性' },
  { voice: 'zh-CN-YunxiNeural',    name: '云希', desc: '年轻男性' },
  { voice: 'zh-CN-YunxiaNeural',   name: '云夏', desc: '少年男性' },
  { voice: 'zh-CN-liaoning-XiaobeiNeural', name: '晓北', desc: '东北话' },
  { voice: 'zh-CN-shaanxi-XiaoniNeural',   name: '晓妮', desc: '陕西话' },
]

// ── VRM 模型预设 ────────────────────────────────────────────────────
export const VRM_PRESETS = [
  { id: 'avatar_b',   label: 'AvatarSample B', icon: '🧍', desc: '本地 VRM 模型，白色背景，手自然下垂' },
  { id: 'official',   label: '官方示例',  icon: '🧍', desc: 'three-vrm 默认模型' },
  { id: 'vroid_base', label: 'VRoid 素体', icon: '👩', desc: 'VRoid Studio 女性素体' },
  { id: 'custom',     label: '自定义',    icon: '🔧', desc: '粘贴 URL 或选择本地文件' },
]

export const SCENE_PRESETS = [
  { id: 'auto',  label: '自动（跟随模型）' },
  { id: 'dark',  label: '深色空间' },
  { id: 'light', label: '明亮空间' },
]

// 模型预设 URL 映射
export const VRM_PRESET_URLS = {
  official:   'https://cdn.jsdelivr.net/gh/pixiv/three-vrm@3.5.1/packages/three-vrm/examples/models/VRM1_Constraint_Twist_Sample.vrm',
  vroid_base: window.electronAPI?.isElectron ? './models/vroid_female.vrm'   : '/models/vroid_female.vrm',
  avatar_b:   window.electronAPI?.isElectron ? './models/AvatarSample_B.vrm' : '/models/AvatarSample_B.vrm',
  glb_custom: window.electronAPI?.isElectron ? './models/textured_mesh.glb'  : '/models/textured_mesh.glb',
}

// ── localStorage 读写 ───────────────────────────────────────────────
export function loadSettings() {
  try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') } catch { return {} }
}

export function saveSettings(partial) {
  const existing = loadSettings()
  const data = { ...existing, ...partial }
  localStorage.setItem(STORAGE_KEY, JSON.stringify(data))
  return data
}

// ── VRM/场景 辅助函数 ───────────────────────────────────────────────
export function getVrmPreset() {
  const s = loadSettings()
  return (s.vrmPresetUserSet && s.vrmPreset) ? s.vrmPreset : 'avatar_b'
}

export function getDefaultVrmUrl() {
  const preset = getVrmPreset()
  if (preset === 'custom') return loadSettings().vrmUrl || ''
  return VRM_PRESET_URLS[preset] || VRM_PRESET_URLS.avatar_b
}

export function isGLBModel(url) {
  return url?.toLowerCase().endsWith('.glb') && getVrmPreset() === 'glb_custom'
}

export function getScenePreset() {
  const settings = loadSettings()
  const scene = settings.scenePreset || 'auto'
  if (scene !== 'auto') return scene
  const vrm = getVrmPreset()
  return (vrm === 'vroid_base' || vrm === 'glb_custom' || vrm === 'avatar_b') ? 'light' : 'dark'
}
