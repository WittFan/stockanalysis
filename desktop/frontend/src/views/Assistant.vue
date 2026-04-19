<template>
  <div class="agent-view">

    <!-- ── 左：3D 角色 ─────────────────────────────────── -->
    <div class="character-panel" ref="containerRef" :style="sceneCssVars">
      <canvas ref="canvasRef" class="three-canvas" />

      <!-- VRM 加载中 -->
      <div class="vrm-overlay" v-if="vrmLoading">
        <div class="vrm-spinner" />
        <div class="vrm-load-text">加载模型 {{ vrmProgress }}%</div>
        <div class="vrm-progress-bar">
          <div class="vrm-progress-fill" :style="{ width: vrmProgress + '%' }" />
        </div>
      </div>

      <!-- VRM 加载失败 -->
      <div class="vrm-overlay vrm-overlay--error" v-else-if="vrmError">
        <div style="font-size:28px">⚠️</div>
        <div class="vrm-err-msg">{{ vrmError }}</div>
        <button class="vrm-retry-btn" @click="retryLoadVRM">重试</button>
        <div class="vrm-err-hint">可在「设置」中配置 VRM 模型地址</div>
      </div>

      <!-- 动作按钮 -->
      <div class="anim-controls" v-if="!vrmLoading && !vrmError">
        <button class="anim-btn" :class="{ active: animMode === 'idle' }" @click="setAnim('idle')" title="待机">🧍</button>
        <button class="anim-btn" :class="{ active: animMode === 'wave' }" @click="setAnim('wave')" title="挥手">👋</button>
        <button class="anim-btn" :class="{ active: animMode === 'bow' }" @click="setAnim('bow')" title="鞠躬">🙇</button>
        <button class="anim-btn" :class="{ active: animMode === 'happy' }" @click="setAnim('happy')" title="开心">🙌</button>
      </div>

      <div class="character-badge">
        <span class="badge-dot" :class="charState" />
        <span class="badge-name">助理小姐</span>
        <span class="badge-status">{{ statusText }}</span>
      </div>
      <div class="no-settings-tip" v-if="!hasSettings">
        请先在「设置」配置 API Key
      </div>
    </div>

    <!-- ── 右：Agent 对话（Claude Code 风格）──────────── -->
    <div class="agent-panel">

      <!-- 顶部栏 -->
      <div class="agent-header">
        <div class="header-left">
          <span class="agent-title">Agent</span>
          <span class="session-badge" v-if="currentSessionId">
            <span class="session-dot" />
            <span class="session-id">{{ currentSessionId.slice(0, 8) }}</span>
          </span>
        </div>
        <div class="header-right">
          <span class="model-tag" v-if="currentModel">{{ currentModel }}</span>
          <button class="hdr-btn" @click="clearHistory" title="新建会话">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            新建
          </button>
        </div>
      </div>

      <!-- Feed 区域 -->
      <div class="feed" ref="messagesRef">

        <!-- 空状态 -->
        <div v-if="!displayMessages.length" class="empty-state">
          <div class="empty-logo">
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><path d="M12 8v4l3 3"/>
            </svg>
          </div>
          <div class="empty-title">量化投研智能体</div>
          <div class="empty-sub">分析股票 · 查询行情 · 回测策略</div>
          <div class="suggestions">
            <button v-for="s in suggestions" :key="s" class="suggest-btn" @click="fillSuggest(s)">
              {{ s }}
            </button>
          </div>
        </div>

        <template v-for="msg in displayMessages" :key="msg.id">

          <!-- ── 用户输入行 ── -->
          <div v-if="msg.role === 'user'" class="feed-row feed-user">
            <span class="feed-prompt">&gt;</span>
            <div class="feed-user-text" v-html="md(msg.content)" />
          </div>

          <!-- ── 助理输出块 ── -->
          <div v-else-if="msg.role === 'assistant'" class="feed-row feed-assistant">

            <!-- 工具调用卡片 -->
            <div
              v-for="(tc, i) in msg.toolCalls" :key="tc.id"
              class="tool-card" :class="'tool-' + tc.status"
            >
              <!-- 卡片头 -->
              <div class="tool-card-head" @click="tc.open = !tc.open">
                <span class="tool-step">{{ i + 1 }}</span>
                <span class="tool-icon">{{ toolIcon(tc.name) }}</span>
                <span class="tool-name">{{ tc.name }}</span>
                <span class="tool-status-dot" :class="tc.status" />
                <span class="tool-status-label" :class="tc.status">
                  {{ tc.status === 'running' ? '运行中' : tc.status === 'done' ? '完成' : '失败' }}
                </span>
                <span class="tool-chevron" :class="{ open: tc.open }">
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><polyline points="6 9 12 15 18 9"/></svg>
                </span>
              </div>

              <!-- 卡片内容（可折叠）-->
              <Transition name="fold">
                <div v-show="tc.open" class="tool-card-body">
                  <!-- 参数 -->
                  <div class="tool-section">
                    <span class="tool-section-label">INPUT</span>
                    <pre class="tool-code">{{ fmtJson(tc.arguments) }}</pre>
                  </div>
                  <!-- 结果 -->
                  <div v-if="tc.result !== undefined" class="tool-section">
                    <span class="tool-section-label">OUTPUT</span>
                    <div class="tool-output" v-html="md(String(tc.result))" />
                  </div>
                </div>
              </Transition>
            </div>

            <!-- 文字回复 -->
            <div v-if="msg.content || msg.streaming" class="feed-text">
              <span v-html="md(msg.content)" />
              <span v-if="msg.streaming" class="cursor" />
            </div>

            <span v-if="!msg.streaming && msg.content" class="feed-time">{{ msg.time }}</span>
          </div>
        </template>

        <!-- 思考动效 -->
        <div v-if="isThinking && !isStreaming" class="feed-row feed-assistant">
          <div class="thinking">
            <span class="thinking-label">思考中</span>
            <span class="thinking-dots"><i/><i/><i/></span>
          </div>
        </div>

      </div>

      <!-- 输入区 -->
      <div class="input-bar">
        <div class="input-wrap" :class="{ focused: inputText.trim() }">
          <span class="input-prompt">&gt;</span>
          <textarea
            ref="inputRef"
            v-model="inputText"
            class="agent-input"
            :disabled="isLoading"
            placeholder="输入指令... (Enter 发送，Shift+Enter 换行)"
            @keydown.enter.exact.prevent="sendMessage"
            @input="autoResize"
            rows="1"
          />
          <button class="send-btn" :disabled="isLoading || !inputText.trim()" @click="sendMessage">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
              <line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/>
            </svg>
          </button>
        </div>
        <div class="input-footer">
          <span class="input-hint">Enter 发送 · Shift+Enter 换行</span>
          <span class="input-tools">
            <span v-for="t in toolDefs.slice(0,3)" :key="t.name" class="input-tool-chip">{{ t.icon }} {{ t.label }}</span>
            <span class="input-tool-chip">🗄️ 金融数据</span>
          </span>
        </div>
      </div>

    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { VRMLoaderPlugin, VRMUtils, VRMExpressionPresetName, VRMHumanBoneName } from '@pixiv/three-vrm'
import {
  loadSettings,
  getDefaultVrmUrl,
  getVrmPreset,
  isGLBModel,
  getScenePreset,
} from '@/composables/useSettings.js'
import { useTTS } from '@/composables/useTTS.js'
import { useChat, fmtJson } from '@/composables/useChat.js'
import { md } from '@/utils/markdown.js'

// 场景配置表
const SCENE_CONFIGS = {
  dark: {
    bg: 0x0d0d1a,
    fog: { color: 0x0d0d1a, density: 0.04 },
    exposure: 1.2,
    ambient: { color: 0x303050, intensity: 1.0 },
    key: { color: 0xfff0e0, intensity: 2.5, pos: [1.5, 3, 2] },
    fill: { color: 0x8040ff, intensity: 2.5, pos: [-2, 2, -1], type: 'point', distance: 8 },
    rim: { color: 0x4090ff, intensity: 1.2, pos: [0, 2.5, -2], type: 'point', distance: 6 },
    front: { color: 0xffe8f0, intensity: 0.8, pos: [0, 1.5, 2.5], type: 'point', distance: 5 },
    diskColor: 0x6030ff,
    diskOpacity: 0.1,
    particleColor: 0x9070ff,
    particleOpacity: 0.6,
    panelBg: '#0d0d1a',
    overlayBg: 'rgba(13, 13, 26, 0.85)',
    overlayBgError: 'rgba(13, 13, 26, 0.92)',
    overlayText: 'rgba(255,255,255,0.7)',
    progressBg: 'rgba(255,255,255,0.1)',
    errColor: '#ff9090',
    btnColor: '#c090ff',
    btnBg: 'rgba(160,100,255,0.12)',
    btnBorder: 'rgba(160,100,255,0.5)',
    btnHoverBg: 'rgba(160,100,255,0.25)',
    hintColor: 'rgba(255,255,255,0.3)',
    animBg: 'rgba(13,13,30,.6)',
    animBorder: 'rgba(255,255,255,.1)',
    animHover: 'rgba(255,255,255,.1)',
    animActive: 'rgba(160,100,255,.35)',
    badgeBg: 'rgba(13,13,30,.75)',
    badgeBorder: 'rgba(255,255,255,.12)',
    badgeName: 'rgba(255,255,255,.9)',
    badgeStatus: 'rgba(255,255,255,.5)',
    tipBg: 'rgba(255,80,80,.18)',
    tipBorder: 'rgba(255,80,80,.4)',
    tipColor: '#ff9090',
  },
  light: {
    bg: 0xffffff,
    exposure: 1.25,
    ambient: { color: 0xfff8f5, intensity: 0.85 },
    key: { color: 0xffecd8, intensity: 1.9, pos: [1.2, 3, 1.8] },
    fill: { color: 0xd8e8ff, intensity: 0.9, pos: [-1.5, 2, 1.5], type: 'directional' },
    rim: { color: 0xffc0a0, intensity: 0.6, pos: [0, 2, -2], type: 'directional' },
    front: { color: 0xffffff, intensity: 0.45, pos: [0, 1.2, 2.2], type: 'point', distance: 5 },
    diskColor: 0xd0d0e0,
    diskOpacity: 0.15,
    particleColor: 0xa090c0,
    particleOpacity: 0.25,
    panelBg: '#ffffff',
    overlayBg: 'rgba(255, 255, 255, 0.88)',
    overlayBgError: 'rgba(255, 255, 255, 0.95)',
    overlayText: 'rgba(60,60,80,0.8)',
    progressBg: 'rgba(0,0,0,0.08)',
    errColor: '#c04040',
    btnColor: '#7030a0',
    btnBg: 'rgba(160,100,255,0.12)',
    btnBorder: 'rgba(160,100,255,0.5)',
    btnHoverBg: 'rgba(160,100,255,0.22)',
    hintColor: 'rgba(80,80,100,0.5)',
    animBg: 'rgba(255,255,255,.7)',
    animBorder: 'rgba(0,0,0,.08)',
    animHover: 'rgba(0,0,0,.05)',
    animActive: 'rgba(160,100,255,.25)',
    badgeBg: 'rgba(255,255,255,.85)',
    badgeBorder: 'rgba(0,0,0,.1)',
    badgeName: 'rgba(40,40,60,.9)',
    badgeStatus: 'rgba(80,80,100,.6)',
    tipBg: 'rgba(255,80,80,.12)',
    tipBorder: 'rgba(255,80,80,.3)',
    tipColor: '#c04040',
  }
}

const effectiveScenePreset = computed(() => getScenePreset())
const sceneCssVars = computed(() => {
  const cfg = SCENE_CONFIGS[effectiveScenePreset.value]
  return {
    '--panel-bg': cfg.panelBg,
    '--overlay-bg': cfg.overlayBg,
    '--overlay-bg-error': cfg.overlayBgError,
    '--overlay-text': cfg.overlayText,
    '--progress-bg': cfg.progressBg,
    '--err-color': cfg.errColor,
    '--btn-color': cfg.btnColor,
    '--btn-bg': cfg.btnBg,
    '--btn-border': cfg.btnBorder,
    '--btn-hover-bg': cfg.btnHoverBg,
    '--hint-color': cfg.hintColor,
    '--anim-bg': cfg.animBg,
    '--anim-border': cfg.animBorder,
    '--anim-hover': cfg.animHover,
    '--anim-active': cfg.animActive,
    '--badge-bg': cfg.badgeBg,
    '--badge-border': cfg.badgeBorder,
    '--badge-name': cfg.badgeName,
    '--badge-status': cfg.badgeStatus,
    '--tip-bg': cfg.tipBg,
    '--tip-border': cfg.tipBorder,
    '--tip-color': cfg.tipColor,
  }
})

// ── 对话状态 ──────────────────────────────────────────────
const containerRef    = ref(null)
const canvasRef       = ref(null)
const messagesRef     = ref(null)
const inputRef        = ref(null)
const charState       = ref('idle')   // idle | thinking | talking

const statusText = computed(() => {
  if (charState.value === 'thinking') return '思考中...'
  if (charState.value === 'talking')  return '回复中'
  return '在线'
})

const suggestions = ['帮我分析一下贵州茅台', '市盈率多少算合理？', '计算一下 sqrt(1024) + 3^4', '现在几点了？']

// ── TTS ───────────────────────────────────────────────────
const { speak, stopSpeaking, getAudioVolume } = useTTS({
  onStateChange: (state) => { charState.value = state },
})

// ── Chat ──────────────────────────────────────────────────
const {
  inputText, isLoading, isThinking, isStreaming,
  displayMessages, currentSessionId,
  hasSettings, currentModel, toolDefs, toolIcon,
  sendMessage, clearHistory, fillSuggest,
  scrollToBottom, autoResize,
} = useChat({
  speak,
  stopSpeaking,
  onStateChange: (state) => { charState.value = state },
  messagesRef,
  inputRef,
})

// ── Three.js + VRM ────────────────────────────────────────
let renderer, scene, camera, animFrameId, clock
let currentVRM = null
let currentGLB = null         // 纯 GLB 场景（非 VRM）
let glbEmotionLight = null    // GLB 情绪点光源
let glbBaseY = 0              // GLB 模型初始 Y 坐标

const vrmLoading  = ref(false)
const vrmError    = ref('')
const vrmProgress = ref(0)
let lastVrmUrl = ''

// ── 程序化动作系统 ────────────────────────────────────────
const animMode = ref('idle')   // idle | wave | bow | happy
let animTimer = 0

// 动画状态
let blinkTimer    = 0
let blinkInterval = 3 + Math.random() * 3
let isBlinking    = false

// 表情平滑插值目标
const exprTargets = {
  [VRMExpressionPresetName.Happy]:    0,
  [VRMExpressionPresetName.Relaxed]:  0,
  [VRMExpressionPresetName.Surprised]:0,
  [VRMExpressionPresetName.Sad]:      0,
}

// 鼠标视线目标
const lookAtTarget = new THREE.Object3D()

function initThree() {
  const container = containerRef.value
  const w = container.clientWidth, h = container.clientHeight
  const sceneCfg = SCENE_CONFIGS[effectiveScenePreset.value]

  scene = new THREE.Scene()
  scene.background = new THREE.Color(sceneCfg.bg)
  if (sceneCfg.fog) {
    scene.fog = new THREE.FogExp2(sceneCfg.fog.color, sceneCfg.fog.density)
  } else {
    scene.fog = null
  }

  camera = new THREE.PerspectiveCamera(22, w / h, 0.1, 50)
  camera.position.set(0, 0.36, 2.0)
  camera.lookAt(0, 0.34, 0)

  renderer = new THREE.WebGLRenderer({ canvas: canvasRef.value, antialias: true, alpha: false })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = true
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = sceneCfg.exposure

  // 灯光
  scene.add(new THREE.AmbientLight(sceneCfg.ambient.color, sceneCfg.ambient.intensity))

  const key = new THREE.DirectionalLight(sceneCfg.key.color, sceneCfg.key.intensity)
  key.position.set(...sceneCfg.key.pos); key.castShadow = true; scene.add(key)

  const makeLight = (cfg) => {
    if (cfg.type === 'directional') {
      const l = new THREE.DirectionalLight(cfg.color, cfg.intensity)
      l.position.set(...cfg.pos); return l
    }
    const l = new THREE.PointLight(cfg.color, cfg.intensity, cfg.distance || 10)
    l.position.set(...cfg.pos); return l
  }
  scene.add(makeLight(sceneCfg.fill))
  scene.add(makeLight(sceneCfg.rim))
  scene.add(makeLight(sceneCfg.front))

  // 地面光晕
  const diskGeo = new THREE.CircleGeometry(0.6, 48)
  const diskMat = new THREE.MeshBasicMaterial({ color: sceneCfg.diskColor, transparent: true, opacity: sceneCfg.diskOpacity })
  const disk = new THREE.Mesh(diskGeo, diskMat)
  disk.rotation.x = -Math.PI / 2; disk.position.y = -0.01; scene.add(disk)

  // 粒子星场
  const count = 150
  const pos = new Float32Array(count * 3)
  for (let i = 0; i < count * 3; i += 3) {
    pos[i]   = (Math.random() - 0.5) * 12
    pos[i+1] = (Math.random() - 0.5) * 8
    pos[i+2] = (Math.random() - 0.5) * 6 - 4
  }
  const pGeo = new THREE.BufferGeometry()
  pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3))
  scene.add(new THREE.Points(pGeo, new THREE.PointsMaterial({ color: sceneCfg.particleColor, size: 0.022, transparent: true, opacity: sceneCfg.particleOpacity })))

  // lookAt 目标加入场景（放在模型前方 +Z 方向）
  lookAtTarget.position.set(0, 0.62, 2.2)
  scene.add(lookAtTarget)

  // 鼠标追踪
  container.addEventListener('mousemove', onMouseMove)

  clock = new THREE.Clock()
  animate()

  // 尺寸自适应
  window._vrmResizeObs = new ResizeObserver(() => {
    const cw = container.clientWidth, ch = container.clientHeight
    camera.aspect = cw / ch; camera.updateProjectionMatrix()
    renderer.setSize(cw, ch)
  })
  window._vrmResizeObs.observe(container)

  // 加载 VRM
  loadVRM(getDefaultVrmUrl())
}

function onMouseMove(e) {
  const rect = containerRef.value?.getBoundingClientRect()
  if (!rect) return
  const nx = (e.clientX - rect.left) / rect.width
  const ny = (e.clientY - rect.top) / rect.height
  lookAtTarget.position.set((nx - 0.5) * 1.8, 0.75 - ny * 0.5, 2.2)
}

async function loadVRM(url) {
  if (!url) return
  lastVrmUrl = url
  vrmLoading.value = true
  vrmError.value   = ''
  vrmProgress.value = 0

  // 清除旧 VRM 模型
  if (currentVRM) {
    scene.remove(currentVRM.scene)
    VRMUtils.deepDispose(currentVRM.scene)
    currentVRM = null
  }
  // 清除旧 GLB 模型
  if (currentGLB) {
    scene.remove(currentGLB)
    currentGLB.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
        else obj.material.dispose()
      }
    })
    currentGLB = null
  }

  // 纯 GLB 模型（非 VRM）
  if (isGLBModel(url)) {
    const loader = new GLTFLoader()
    try {
      const gltf = await new Promise((resolve, reject) => {
        loader.load(
          url,
          resolve,
          (e) => { if (e.total) vrmProgress.value = Math.round(e.loaded / e.total * 100) },
          reject,
        )
      })

      const glbScene = gltf.scene

      // 自动计算模型包围盒，居中并缩放到合适高度
      const box = new THREE.Box3().setFromObject(glbScene)
      const size = new THREE.Vector3(); box.getSize(size)
      const center = new THREE.Vector3(); box.getCenter(center)
      const targetHeight = 1.6   // 期望显示高度（米）
      const scale = targetHeight / Math.max(size.y, 0.001)
      glbScene.scale.setScalar(scale)

      // 将模型底部对齐地面，XZ 居中
      glbScene.position.set(-center.x * scale, -box.min.y * scale, -center.z * scale)

      scene.add(glbScene)
      currentGLB = glbScene
      glbBaseY   = glbScene.position.y

      // 根据包围球半径自动计算合适相机距离（视角 28°，保证模型整体在画面内）
      const sphere = new THREE.Sphere()
      new THREE.Box3().setFromObject(glbScene).getBoundingSphere(sphere)
      const fovRad = 28 * Math.PI / 180
      const camDist = sphere.radius / Math.tan(fovRad / 2) * 1.3
      camera.fov = 28
      camera.updateProjectionMatrix()
      camera.position.set(0, sphere.center.y, sphere.center.z + camDist)
      camera.lookAt(0, sphere.center.y, sphere.center.z)

      // 情绪点光源：放在模型正面，随状态变色
      if (glbEmotionLight) scene.remove(glbEmotionLight)
      glbEmotionLight = new THREE.PointLight(0x80ff80, 1.2, sphere.radius * 4)
      glbEmotionLight.position.set(0, sphere.center.y, sphere.center.z + sphere.radius * 1.2)
      scene.add(glbEmotionLight)

      // 开启材质 emissive（让颜色切换可见）
      glbScene.traverse(obj => {
        if (obj.isMesh && obj.material) {
          const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
          mats.forEach(m => { if (m.emissive !== undefined) m.emissiveIntensity = 0.12 })
        }
      })

      vrmProgress.value = 100
      vrmLoading.value  = false

    } catch (e) {
      vrmError.value   = e.message || 'GLB 加载失败'
      vrmLoading.value = false
    }
    return
  }

  // VRM 模型
  const loader = new GLTFLoader()
  loader.register(parser => new VRMLoaderPlugin(parser))

  try {
    const gltf = await new Promise((resolve, reject) => {
      loader.load(
        url,
        resolve,
        (e) => { if (e.total) vrmProgress.value = Math.round(e.loaded / e.total * 100) },
        reject,
      )
    })

    const vrm = gltf.userData.vrm
    if (!vrm) throw new Error('不是有效的 VRM 文件')

    VRMUtils.removeUnnecessaryVertices(gltf.scene)
    VRMUtils.combineSkeletons(gltf.scene)

    const vrmPreset = getVrmPreset()

    // 只有 VRoid 等背对摄像机的模型才需要旋转 180°
    if (vrmPreset === 'vroid_base') {
      vrm.scene.rotation.y = Math.PI
    } else {
      vrm.scene.rotation.y = 0
    }

    // 修正 T-pose：手臂和手部下垂到自然姿态
    if (vrmPreset === 'official' || vrmPreset === 'vroid_base' || vrmPreset === 'avatar_b') {
      const lShoulder = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.LeftUpperArm)
      const rShoulder = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.RightUpperArm)
      const lForearm  = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.LeftLowerArm)
      const rForearm  = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.RightLowerArm)
      const lHand     = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.LeftHand)
      const rHand     = vrm.humanoid?.getNormalizedBoneNode(VRMHumanBoneName.RightHand)
      if (lShoulder) lShoulder.rotation.z = -1.15
      if (rShoulder) rShoulder.rotation.z =  1.15
      if (lForearm)  lForearm.rotation.z  = -0.15
      if (rForearm)  rForearm.rotation.z  =  0.15
      if (lHand)     { lHand.rotation.z = -0.15; lHand.rotation.y = -0.25 }
      if (rHand)     { rHand.rotation.z =  0.15; rHand.rotation.y =  0.25 }
    }

    // 设置 lookAt 目标
    if (vrm.lookAt) vrm.lookAt.target = lookAtTarget

    scene.add(vrm.scene)
    currentVRM = vrm
    vrmProgress.value = 100
    vrmLoading.value  = false


  } catch (e) {
    vrmError.value   = e.message || '加载失败'
    vrmLoading.value = false
    // 本地 VRoid 模型缺失时自动 fallback 到官方示例模型
    if (url === VRM_PRESET_URLS.vroid_base) {
      loadVRM(VRM_PRESET_URLS.official)
    }
  }
}

function retryLoadVRM() {
  loadVRM(getDefaultVrmUrl())
}

// ── VRM 每帧动画 ──────────────────────────────────────────

function updateBlink(delta) {
  if (isBlinking) return
  blinkTimer += delta
  if (blinkTimer < blinkInterval) return
  blinkTimer    = 0
  blinkInterval = 2.5 + Math.random() * 3.5
  isBlinking    = true

  const mgr = currentVRM?.expressionManager
  if (!mgr) { isBlinking = false; return }

  // 闭眼 → 开眼 → 完成
  mgr.setValue(VRMExpressionPresetName.BlinkLeft,  1)
  mgr.setValue(VRMExpressionPresetName.BlinkRight, 1)
  setTimeout(() => {
    if (currentVRM?.expressionManager) {
      currentVRM.expressionManager.setValue(VRMExpressionPresetName.BlinkLeft,  0)
      currentVRM.expressionManager.setValue(VRMExpressionPresetName.BlinkRight, 0)
    }
    isBlinking = false
  }, 110)
}

function updateBreathing(t) {
  if (!currentVRM?.humanoid) return
  const breathe = Math.sin(t * 0.9) * 0.012
  const hips  = currentVRM.humanoid.getNormalizedBoneNode(VRMHumanBoneName.Hips)
  const spine = currentVRM.humanoid.getNormalizedBoneNode(VRMHumanBoneName.Spine)
  if (hips)  hips.position.y  = breathe * 0.25
  if (spine) spine.rotation.x = breathe
}

function updateIdleSway(t) {
  if (!currentVRM?.humanoid) return
  const neck = currentVRM.humanoid.getNormalizedBoneNode(VRMHumanBoneName.Neck)
  if (!neck) return
  // 当播放动作时，头部由动作系统接管，不进行 idle 摇摆
  if (animMode.value !== 'idle') return
  const state = charState.value
  if (state === 'thinking') {
    // 思考时头微微侧向
    neck.rotation.z = Math.sin(t * 0.6) * 0.06 + 0.06
    neck.rotation.y = Math.sin(t * 0.4) * 0.04
  } else {
    neck.rotation.z = Math.sin(t * 0.25) * 0.025
    neck.rotation.y = Math.sin(t * 0.38) * 0.03
  }
}

function setAnim(mode) {
  animMode.value = mode
  animTimer = 0
}

function resetPose() {
  if (!currentVRM?.humanoid) return
  const h = currentVRM.humanoid
  const resetBone = (name) => {
    const node = h.getNormalizedBoneNode(name)
    if (node) { node.rotation.set(0, 0, 0); node.position.set(0, 0, 0) }
  }
  // 恢复主要骨骼到初始状态
  resetBone(VRMHumanBoneName.LeftUpperArm)
  resetBone(VRMHumanBoneName.RightUpperArm)
  resetBone(VRMHumanBoneName.LeftLowerArm)
  resetBone(VRMHumanBoneName.RightLowerArm)
  resetBone(VRMHumanBoneName.LeftHand)
  resetBone(VRMHumanBoneName.RightHand)
  resetBone(VRMHumanBoneName.Spine)
  resetBone(VRMHumanBoneName.Hips)
  resetBone(VRMHumanBoneName.Neck)

  // 需要重新应用 T-pose 修正的预设
  const preset = getVrmPreset()
  if (preset !== 'official' && preset !== 'vroid_base' && preset !== 'avatar_b') return
  const lShoulder = h.getNormalizedBoneNode(VRMHumanBoneName.LeftUpperArm)
  const rShoulder = h.getNormalizedBoneNode(VRMHumanBoneName.RightUpperArm)
  const lForearm  = h.getNormalizedBoneNode(VRMHumanBoneName.LeftLowerArm)
  const rForearm  = h.getNormalizedBoneNode(VRMHumanBoneName.RightLowerArm)
  const lHand     = h.getNormalizedBoneNode(VRMHumanBoneName.LeftHand)
  const rHand     = h.getNormalizedBoneNode(VRMHumanBoneName.RightHand)
  if (lShoulder) lShoulder.rotation.z = -1.15
  if (rShoulder) rShoulder.rotation.z =  1.15
  if (lForearm)  lForearm.rotation.z  = -0.15
  if (rForearm)  rForearm.rotation.z  =  0.15
  if (lHand)     { lHand.rotation.z = -0.15; lHand.rotation.y = -0.25 }
  if (rHand)     { rHand.rotation.z =  0.15; rHand.rotation.y =  0.25 }
}

function updateGesture(t, delta) {
  if (!currentVRM?.humanoid) return
  animTimer += delta
  const h = currentVRM.humanoid
  const mode = animMode.value

  // 先将骨骼重置，避免动作叠加
  resetPose()

  if (mode === 'wave') {
    const rUpper = h.getNormalizedBoneNode(VRMHumanBoneName.RightUpperArm)
    const rLower = h.getNormalizedBoneNode(VRMHumanBoneName.RightLowerArm)
    if (rUpper) {
      rUpper.rotation.z = 2.6 + Math.sin(t * 8) * 0.25   // 举起并摆动
      rUpper.rotation.y = -0.3
    }
    if (rLower) rLower.rotation.z = 0.2 + Math.sin(t * 8) * 0.15

    // 头部跟随
    const neck = h.getNormalizedBoneNode(VRMHumanBoneName.Neck)
    if (neck) neck.rotation.y = Math.sin(t * 8) * 0.08
  }
  else if (mode === 'bow') {
    const spine = h.getNormalizedBoneNode(VRMHumanBoneName.Spine)
    const neck  = h.getNormalizedBoneNode(VRMHumanBoneName.Neck)
    const hips  = h.getNormalizedBoneNode(VRMHumanBoneName.Hips)
    // 鞠躬：脊柱前倾，抬头看镜头
    const bowAngle = Math.min(animTimer * 1.5, 0.6)
    if (spine) spine.rotation.x = bowAngle
    if (neck)  neck.rotation.x  = -bowAngle * 0.8
    if (hips)  hips.position.y  = -bowAngle * 0.05

    // 3秒后自动恢复待机
    if (animTimer > 3) setAnim('idle')
  }
  else if (mode === 'happy') {
    const rUpper = h.getNormalizedBoneNode(VRMHumanBoneName.RightUpperArm)
    const lUpper = h.getNormalizedBoneNode(VRMHumanBoneName.LeftUpperArm)
    const rLower = h.getNormalizedBoneNode(VRMHumanBoneName.RightLowerArm)
    const lLower = h.getNormalizedBoneNode(VRMHumanBoneName.LeftLowerArm)
    const hips   = h.getNormalizedBoneNode(VRMHumanBoneName.Hips)
    const neck   = h.getNormalizedBoneNode(VRMHumanBoneName.Neck)

    const jump = Math.abs(Math.sin(t * 6)) * 0.04
    if (hips) hips.position.y = jump

    if (rUpper) { rUpper.rotation.z = 2.4 + Math.sin(t * 10) * 0.15; rUpper.rotation.y = -0.2 }
    if (lUpper) { lUpper.rotation.z = -2.4 - Math.sin(t * 10) * 0.15; lUpper.rotation.y = 0.2 }
    if (rLower) rLower.rotation.z = 0.3
    if (lLower) lLower.rotation.z = -0.3
    if (neck) neck.rotation.x = -0.15

    // 4秒后自动恢复待机
    if (animTimer > 4) setAnim('idle')
  }
}

function updateLipSync(t) {
  const mgr = currentVRM?.expressionManager
  if (!mgr) return
  const state = charState.value

  if (state === 'talking') {
    // 基于真实音频音量驱动口型（替代原来的正弦波模拟）
    const volume = getAudioVolume()
    // 添加轻微随机抖动，让口型更自然
    const jitter = Math.sin(t * 23) * 0.04
    const aa = Math.max(0, Math.min(1, volume * 1.3 + jitter - 0.05))
    const ih = Math.max(0, Math.min(1, volume * 0.7 + jitter * 0.5 - 0.02))
    const ou = Math.max(0, Math.min(1, volume * 0.4 + Math.sin(t * 17) * 0.08))
    mgr.setValue(VRMExpressionPresetName.Aa, aa)
    mgr.setValue(VRMExpressionPresetName.Ih, ih)
    mgr.setValue(VRMExpressionPresetName.Ou, ou)
  } else {
    mgr.setValue(VRMExpressionPresetName.Aa, 0)
    mgr.setValue(VRMExpressionPresetName.Ih, 0)
    mgr.setValue(VRMExpressionPresetName.Ou, 0)
  }
}

function updateExpression(delta) {
  const mgr = currentVRM?.expressionManager
  if (!mgr) return
  const state = charState.value

  // 根据状态设置目标表情权重
  exprTargets[VRMExpressionPresetName.Happy]     = state === 'talking'  ? 0.55 : 0
  exprTargets[VRMExpressionPresetName.Relaxed]   = state === 'idle'     ? 0.35 : 0
  exprTargets[VRMExpressionPresetName.Surprised] = state === 'thinking' ? 0.12 : 0
  exprTargets[VRMExpressionPresetName.Sad]       = 0

  // 平滑插值到目标
  for (const [name, target] of Object.entries(exprTargets)) {
    const cur = mgr.getValue(name) ?? 0
    const next = cur + (target - cur) * Math.min(delta * 4, 1)
    mgr.setValue(name, Math.max(0, Math.min(1, next)))
  }
}

// vrm.update() 之后再修正手臂，直接写 raw bone 绕过约束系统
function applyArmCorrection() {
  if (!currentVRM?.humanoid) return
  const preset = getVrmPreset()
  if (preset !== 'official' && preset !== 'vroid_base' && preset !== 'avatar_b') return

  // getRawBoneNode 拿到实际渲染骨骼，不受 VRM 约束层影响
  const getRaw = name => currentVRM.humanoid.getRawBoneNode?.(name)
    ?? currentVRM.humanoid.getNormalizedBoneNode(name)

  const lShoulder = getRaw(VRMHumanBoneName.LeftUpperArm)
  const rShoulder = getRaw(VRMHumanBoneName.RightUpperArm)
  const lForearm  = getRaw(VRMHumanBoneName.LeftLowerArm)
  const rForearm  = getRaw(VRMHumanBoneName.RightLowerArm)
  const lHand     = getRaw(VRMHumanBoneName.LeftHand)
  const rHand     = getRaw(VRMHumanBoneName.RightHand)

  const mode = animMode.value
  // 只在待机时强制修正，动作模式由 updateGesture 接管
  if (mode === 'idle') {
    if (lShoulder) lShoulder.rotation.z = -1.15
    if (rShoulder) rShoulder.rotation.z =  1.15
    if (lForearm)  lForearm.rotation.z  = -0.15
    if (rForearm)  rForearm.rotation.z  =  0.15
    if (lHand)     { lHand.rotation.z = -0.15; lHand.rotation.y = -0.25 }
    if (rHand)     { rHand.rotation.z =  0.15; rHand.rotation.y =  0.25 }
  }
}

// ── GLB 程序化动画 ────────────────────────────────────────

// 情绪光颜色配置
const GLB_EMOTION = {
  idle:     { light: new THREE.Color(0x60ff80), intensity: 0.9,  emissive: new THREE.Color(0x041a08) },
  thinking: { light: new THREE.Color(0x4090ff), intensity: 1.4,  emissive: new THREE.Color(0x040c20) },
  talking:  { light: new THREE.Color(0xff80b0), intensity: 1.8,  emissive: new THREE.Color(0x1a0808) },
}

// 当前插值状态
let glbLightColor  = new THREE.Color(0x60ff80)
let glbEmissive    = new THREE.Color(0x041a08)

function updateGLBAnimation(t, delta) {
  if (!currentGLB) return
  const state  = charState.value
  const cfg    = GLB_EMOTION[state] || GLB_EMOTION.idle

  // 1. 整体姿态动画
  if (state === 'talking') {
    // 说话：上下弹跳 + 左右轻摆
    currentGLB.position.y = glbBaseY + Math.abs(Math.sin(t * 10)) * 0.025
    currentGLB.rotation.z = Math.sin(t * 9) * 0.035
    currentGLB.rotation.y = Math.sin(t * 0.5) * 0.15
  } else if (state === 'thinking') {
    // 思考：慢速左右倾斜，微微点头
    currentGLB.position.y = glbBaseY + Math.sin(t * 1.2) * 0.008
    currentGLB.rotation.z = Math.sin(t * 1.5) * 0.07 + 0.05
    currentGLB.rotation.y = Math.sin(t * 0.4) * 0.1
  } else {
    // 待机：缓慢自转 + 呼吸起伏
    currentGLB.position.y = glbBaseY + Math.sin(t * 0.9) * 0.008
    currentGLB.rotation.z = Math.sin(t * 0.5) * 0.018
    currentGLB.rotation.y = Math.sin(t * 0.3) * 0.25
  }

  // 2. 情绪光颜色平滑插值
  glbLightColor.lerp(cfg.light, delta * 3)
  glbEmissive.lerp(cfg.emissive, delta * 3)
  if (glbEmotionLight) {
    glbEmotionLight.color.copy(glbLightColor)
    glbEmotionLight.intensity += (cfg.intensity - glbEmotionLight.intensity) * delta * 3
    // 说话时光源轻微脉动
    if (state === 'talking') {
      glbEmotionLight.intensity = cfg.intensity + Math.sin(t * 12) * 0.3
    }
  }

  // 3. 材质 emissive 颜色
  currentGLB.traverse(obj => {
    if (obj.isMesh && obj.material) {
      const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
      mats.forEach(m => { if (m.emissive !== undefined) m.emissive.copy(glbEmissive) })
    }
  })
}

function animate() {
  animFrameId = requestAnimationFrame(animate)
  const delta = clock.getDelta()
  const t     = clock.getElapsedTime()

  if (currentVRM) {
    updateBlink(delta)
    updateBreathing(t)
    updateGesture(t, delta)
    updateIdleSway(t)
    updateLipSync(t)
    updateExpression(delta)
    currentVRM.update(delta)
    // VRM 约束（vrm.update）执行后再覆写手臂旋转，防止约束系统还原 T-pose
    applyArmCorrection()
  }

  if (currentGLB) {
    updateGLBAnimation(t, delta)
  }

  renderer.render(scene, camera)
}

// ── 生命周期 ──────────────────────────────────────────────
onMounted(() => {
  nextTick(() => { initThree() })
})
onUnmounted(() => {
  cancelAnimationFrame(animFrameId)
  if (currentVRM) { VRMUtils.deepDispose(currentVRM.scene); currentVRM = null }
  if (glbEmotionLight) { scene?.remove(glbEmotionLight); glbEmotionLight = null }
  if (currentGLB) {
    scene?.remove(currentGLB)
    currentGLB.traverse(obj => {
      if (obj.geometry) obj.geometry.dispose()
      if (obj.material) {
        if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose())
        else obj.material.dispose()
      }
    })
    currentGLB = null
  }
  renderer?.dispose()
  if (window._vrmResizeObs) { window._vrmResizeObs.disconnect(); delete window._vrmResizeObs }
  containerRef.value?.removeEventListener('mousemove', onMouseMove)
})
</script>

<style scoped>
/* ── 布局 ─────────────────────────────────────────────── */
.agent-view {
  display: flex;
  height: calc(100vh - 44px);
  overflow: hidden;
  background: var(--bg-secondary);
}

/* ── 左：角色面板 ────────────────────────────────────── */
.character-panel {
  flex: 0 0 36%;
  position: relative;
  background: var(--panel-bg, #ffffff);
  overflow: hidden;
}
.three-canvas { width: 100%; height: 100%; display: block; }

/* VRM 加载/错误遮罩 */
.vrm-overlay {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 12px;
  background: var(--overlay-bg, rgba(255, 255, 255, 0.88));
  backdrop-filter: blur(6px);
  z-index: 10;
  padding: 20px;
}
.vrm-overlay--error { background: var(--overlay-bg-error, rgba(255, 255, 255, 0.95)); }

.vrm-spinner {
  width: 36px; height: 36px;
  border: 3px solid rgba(160, 100, 255, 0.25);
  border-top-color: #a064ff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.vrm-load-text {
  font-size: 13px; color: var(--overlay-text, rgba(60,60,80,0.8)); font-weight: 500;
}
.vrm-progress-bar {
  width: 160px; height: 3px;
  background: var(--progress-bg, rgba(0,0,0,0.08)); border-radius: 2px; overflow: hidden;
}
.vrm-progress-fill {
  height: 100%; background: #a064ff;
  border-radius: 2px; transition: width 0.3s ease;
}
.vrm-err-msg {
  font-size: 12px; color: var(--err-color, #c04040); text-align: center;
  max-width: 220px; line-height: 1.5;
}
.vrm-retry-btn {
  padding: 5px 16px; border: 1px solid var(--btn-border, rgba(160,100,255,0.5));
  border-radius: 20px; background: var(--btn-bg, rgba(160,100,255,0.12));
  color: var(--btn-color, #7030a0); font-size: 12px; cursor: pointer; font-family: inherit;
  transition: all .15s;
}
.vrm-retry-btn:hover { background: var(--btn-hover-bg, rgba(160,100,255,0.22)); }
.vrm-err-hint { font-size: 11px; color: var(--hint-color, rgba(80,80,100,0.5)); }

/* 动作按钮 */
.anim-controls {
  position: absolute; bottom: 56px; left: 50%; transform: translateX(-50%);
  display: flex; gap: 8px;
  background: var(--anim-bg, rgba(255,255,255,.7)); backdrop-filter: blur(10px);
  border: .5px solid var(--anim-border, rgba(0,0,0,.08)); border-radius: 20px;
  padding: 5px 8px; z-index: 5;
}
.anim-btn {
  width: 32px; height: 32px; border-radius: 50%;
  border: none; background: transparent;
  font-size: 15px; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all .15s; filter: grayscale(0.3);
}
.anim-btn:hover { background: var(--anim-hover, rgba(0,0,0,.05)); filter: grayscale(0); }
.anim-btn.active { background: var(--anim-active, rgba(160,100,255,.25)); filter: grayscale(0); box-shadow: 0 0 8px var(--anim-active, rgba(160,100,255,.35)); }

/* 角色状态徽章 */
.character-badge {
  position: absolute; bottom: 20px; left: 50%; transform: translateX(-50%);
  display: flex; align-items: center; gap: 7px;
  background: var(--badge-bg, rgba(255,255,255,.85)); backdrop-filter: blur(12px);
  border: .5px solid var(--badge-border, rgba(0,0,0,.1)); border-radius: 20px;
  padding: 6px 14px; white-space: nowrap; z-index: 5;
}
.badge-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #4cd964; box-shadow: 0 0 7px #4cd96488; flex-shrink: 0;
}
.badge-dot.thinking { background: #ffcc00; box-shadow: 0 0 7px #ffcc0088; animation: pulse .8s ease-in-out infinite; }
.badge-dot.talking  { background: #5ac8fa; box-shadow: 0 0 7px #5ac8fa88; animation: pulse .5s ease-in-out infinite; }
.badge-name { font-size: 13px; font-weight: 600; color: var(--badge-name, rgba(40,40,60,.9)); }
.badge-status { font-size: 11px; color: var(--badge-status, rgba(80,80,100,.6)); }
@keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:.5;transform:scale(.8)} }

.no-settings-tip {
  position: absolute; top: 14px; left: 50%; transform: translateX(-50%);
  background: var(--tip-bg, rgba(255,80,80,.18)); border: .5px solid var(--tip-border, rgba(255,80,80,.4));
  border-radius: 10px; padding: 6px 14px; font-size: 12px; color: var(--tip-color, #ff9090);
  white-space: nowrap; backdrop-filter: blur(8px); z-index: 5;
}

/* ── 右：Agent 面板（Claude Code 风格）──────────────── */
.agent-panel {
  flex: 1; display: flex; flex-direction: column;
  background: var(--bg-primary);
  border-left: 1px solid var(--separator);
  min-width: 0; font-size: var(--size-body);
}

/* ── 顶栏 ───────────────────────────────────────────── */
.agent-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 16px; height: 40px;
  border-bottom: 1px solid var(--separator);
  flex-shrink: 0;
}
.header-left { display: flex; align-items: center; gap: 10px; }
.agent-title {
  font-size: 13px; font-weight: 600;
  color: var(--label); letter-spacing: -.01em;
}
.session-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: var(--fill); border-radius: 4px;
  padding: 1px 7px;
}
.session-dot {
  width: 5px; height: 5px; border-radius: 50%; background: #34c759; flex-shrink: 0;
}
.session-id {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 10px; color: var(--label-muted); letter-spacing: .03em;
}
.header-right { display: flex; align-items: center; gap: 8px; }
.model-tag {
  font-size: 11px; color: var(--label-muted);
  font-family: 'SF Mono', Menlo, monospace;
  padding: 1px 0;
}
.hdr-btn {
  display: inline-flex; align-items: center; gap: 4px;
  height: 26px; padding: 0 10px;
  border: 1px solid var(--separator-opaque); border-radius: 5px;
  background: var(--bg-primary); color: var(--label-2);
  font-size: 12px; font-family: inherit; cursor: pointer;
  transition: border-color .12s, color .12s;
}
.hdr-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ── Feed（消息流）────────────────────────────────── */
.feed {
  flex: 1; overflow-y: auto; padding: 0;
  display: flex; flex-direction: column;
}

/* ── 空状态 ─────────────────────────────────────── */
.empty-state {
  flex: 1; display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center; padding: 48px 24px; gap: 0;
}
.empty-logo {
  color: var(--label-muted); opacity: .4; margin-bottom: 16px;
}
.empty-title {
  font-size: 15px; font-weight: 600; color: var(--label);
  margin-bottom: 5px; letter-spacing: -.01em;
}
.empty-sub {
  font-size: 12px; color: var(--label-muted); margin-bottom: 28px;
}
.suggestions { display: flex; flex-wrap: wrap; gap: 7px; justify-content: center; }
.suggest-btn {
  border: 1px solid var(--separator-opaque);
  background: var(--bg-secondary); border-radius: 6px;
  padding: 5px 12px; font-size: 12px; color: var(--label-2);
  cursor: pointer; font-family: inherit; transition: border-color .12s, color .12s;
}
.suggest-btn:hover { border-color: var(--accent); color: var(--accent); }

/* ── Feed 行共用 ─────────────────────────────────── */
.feed-row {
  padding: 10px 20px;
  border-bottom: 1px solid var(--separator);
  line-height: 1.6;
}
.feed-row:last-child { border-bottom: none; }

/* ── 用户行 ─────────────────────────────────────── */
.feed-user {
  display: flex; align-items: flex-start; gap: 8px;
  background: var(--bg-primary);
}
.feed-prompt {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 13px; font-weight: 700;
  color: var(--accent); flex-shrink: 0; margin-top: 1px;
  user-select: none;
}
.feed-user-text {
  flex: 1; font-size: var(--size-body);
  color: var(--label); word-break: break-word;
}

/* ── 助理行 ─────────────────────────────────────── */
.feed-assistant {
  background: var(--bg-primary);
  display: flex; flex-direction: column; gap: 6px;
}

/* ── 工具卡片（Claude Code 核心元素）────────────── */
.tool-card {
  border-radius: 6px; overflow: hidden;
  border: 1px solid var(--separator-opaque);
  /* 左侧彩色竖线 = Claude Code 标志性设计 */
  border-left: 3px solid var(--separator-opaque);
  font-size: 12px; transition: border-left-color .15s;
}
.tool-card.tool-running { border-left-color: #f0a500; }
.tool-card.tool-done    { border-left-color: #34c759; }
.tool-card.tool-error   { border-left-color: #ff3b30; }

/* 卡片头 */
.tool-card-head {
  display: flex; align-items: center; gap: 7px;
  padding: 6px 10px; cursor: pointer; user-select: none;
  background: var(--bg-secondary); transition: background .1s;
}
.tool-card-head:hover { background: var(--fill); }

.tool-step {
  width: 16px; height: 16px; border-radius: 50%;
  background: var(--fill-2); color: var(--label-muted);
  font-size: 9px; font-weight: 700; display: flex;
  align-items: center; justify-content: center; flex-shrink: 0;
}
.tool-icon { font-size: 13px; flex-shrink: 0; }
.tool-name {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px; font-weight: 600; color: var(--label);
  flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}

/* 状态点 */
.tool-status-dot {
  width: 6px; height: 6px; border-radius: 50%; flex-shrink: 0;
}
.tool-status-dot.running {
  background: #f0a500;
  animation: tool-pulse .8s ease-in-out infinite;
}
.tool-status-dot.done  { background: #34c759; }
.tool-status-dot.error { background: #ff3b30; }
@keyframes tool-pulse { 0%,100%{opacity:1} 50%{opacity:.3} }

/* 状态标签 */
.tool-status-label {
  font-size: 10px; font-weight: 500;
}
.tool-status-label.running { color: #f0a500; }
.tool-status-label.done    { color: #34c759; }
.tool-status-label.error   { color: #ff3b30; }

/* 展开箭头 */
.tool-chevron {
  color: var(--label-muted); flex-shrink: 0;
  display: flex; align-items: center;
  transition: transform .18s ease;
}
.tool-chevron.open { transform: rotate(0deg); }
.tool-chevron:not(.open) { transform: rotate(-90deg); }

/* 卡片内容 */
.tool-card-body { padding: 0; }

.tool-section {
  padding: 8px 10px;
  border-top: 1px solid var(--separator);
}
.tool-section-label {
  font-size: 9px; font-weight: 700; letter-spacing: .08em;
  text-transform: uppercase; color: var(--label-muted);
  margin-bottom: 5px;
}
.tool-code {
  background: var(--bg-primary); border-radius: 4px;
  padding: 6px 8px; margin: 0;
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 11px; color: var(--label-2);
  white-space: pre-wrap; word-break: break-all;
  max-height: 160px; overflow-y: auto;
  border: 1px solid var(--separator);
}
.tool-output {
  font-size: 12px; color: var(--label-2);
  line-height: 1.55; font-family: 'SF Mono', Menlo, monospace;
  white-space: pre-wrap; word-break: break-all;
  max-height: 200px; overflow-y: auto;
}

/* 折叠动画 */
.fold-enter-active, .fold-leave-active { transition: opacity .15s, transform .15s; }
.fold-enter-from, .fold-leave-to { opacity: 0; transform: translateY(-4px); }

/* ── 助理文字回复 ─────────────────────────────────── */
.feed-text {
  font-size: var(--size-body); color: var(--label);
  line-height: 1.65; word-break: break-word;
  padding: 2px 0;
}
.feed-time {
  font-size: 10px; color: var(--label-muted);
  padding-top: 2px;
}

/* ── 打字光标 ─────────────────────────────────────── */
.cursor {
  display: inline-block; width: 2px; height: 1em;
  background: var(--accent); margin-left: 2px; vertical-align: text-bottom;
  animation: blink .7s step-end infinite;
}
@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }

/* ── 思考指示 ─────────────────────────────────────── */
.thinking {
  display: inline-flex; align-items: center; gap: 6px;
}
.thinking-label {
  font-size: 12px; color: var(--label-muted);
  font-style: italic;
}
.thinking-dots {
  display: flex; align-items: center; gap: 3px;
}
.thinking-dots i {
  display: block; width: 4px; height: 4px;
  border-radius: 50%; background: var(--label-muted);
  animation: tdot 1s ease-in-out infinite;
}
.thinking-dots i:nth-child(2) { animation-delay: .18s; }
.thinking-dots i:nth-child(3) { animation-delay: .36s; }
@keyframes tdot { 0%,60%,100%{opacity:.3;transform:scale(.8)} 30%{opacity:1;transform:scale(1)} }

/* ── Markdown ─────────────────────────────────────── */
:deep(.md-pre) {
  background: var(--bg-secondary); border: 1px solid var(--separator-opaque);
  border-radius: 6px; padding: 10px 12px; overflow-x: auto; margin: 6px 0;
}
:deep(.md-code) {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 12px; color: var(--label); line-height: 1.5;
}
:deep(.md-inline) {
  background: var(--fill-2); padding: 1px 5px; border-radius: 3px;
  font-family: 'SF Mono', Menlo, monospace; font-size: .88em;
  color: var(--label-2);
}
:deep(.md-h) { font-weight: 700; margin: 8px 0 4px; }
:deep(h1.md-h) { font-size: 17px; }
:deep(h2.md-h) { font-size: 15px; }
:deep(h3.md-h) { font-size: 13px; }
:deep(li) { margin-left: 18px; }
:deep(strong) { font-weight: 600; }
:deep(a) { color: var(--accent); text-decoration: none; }
:deep(a:hover) { text-decoration: underline; }

/* ── 输入栏 ───────────────────────────────────────── */
.input-bar {
  flex-shrink: 0;
  padding: 12px 16px 10px;
  border-top: 1px solid var(--separator);
  background: var(--bg-primary);
}
.input-wrap {
  display: flex; align-items: flex-end; gap: 0;
  border: 1px solid var(--separator-opaque); border-radius: 8px;
  background: var(--bg-secondary); overflow: hidden;
  transition: border-color .15s;
}
.input-wrap:focus-within { border-color: var(--accent); }

.input-prompt {
  font-family: 'SF Mono', Menlo, monospace;
  font-size: 13px; font-weight: 700; color: var(--label-muted);
  padding: 8px 0 8px 12px; flex-shrink: 0; user-select: none;
  line-height: 1.4; align-self: flex-start; margin-top: 1px;
}
.agent-input {
  flex: 1; min-height: 36px; max-height: 140px;
  padding: 8px 8px 8px 6px;
  border: none; background: transparent;
  font-size: var(--size-body); font-family: inherit;
  color: var(--label); resize: none; outline: none; line-height: 1.4;
  overflow-y: auto;
}
.agent-input::placeholder { color: var(--label-muted); }
.agent-input:disabled { opacity: .5; }

.send-btn {
  width: 34px; height: 34px; border-radius: 6px; border: none; margin: 3px;
  background: var(--accent); color: #fff; cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0; transition: opacity .12s;
  align-self: flex-end;
}
.send-btn:disabled { opacity: .3; cursor: not-allowed; }
.send-btn:not(:disabled):hover { opacity: .85; }

.input-footer {
  display: flex; justify-content: space-between; align-items: center;
  margin-top: 6px; padding: 0 2px;
}
.input-hint {
  font-size: 10px; color: var(--label-muted);
}
.input-tools {
  display: flex; gap: 6px;
}
.input-tool-chip {
  font-size: 10px; color: var(--label-muted);
  background: var(--fill); border-radius: 4px;
  padding: 1px 6px;
}
</style>
