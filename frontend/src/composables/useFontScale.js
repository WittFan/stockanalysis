/**
 * useFontScale —— 字体缩放管理
 *
 * 三档倍率（整体上移一档，默认更大）：
 *   small  = 1.00（原 medium，适合大屏外接显示器）
 *   medium = 1.15（新默认，适合 1920+ 常规显示器）
 *   large  = 1.32（适合笔记本 Retina 小屏）
 *
 * 启动时自动检测：
 *   利用 window.screen.width（CSS 逻辑像素宽度）和
 *   window.devicePixelRatio（物理/逻辑像素比）推断使用场景。
 *   MacBook Retina 屏：dpr ≥ 1.75 且 screenW ≤ 1800 → large
 *   普通 HD 笔记本：screenW ≤ 1366 → large
 *   常规显示器：medium
 *   大尺寸 4K 外接（screenW ≥ 2560, dpr ≤ 1.25）：small
 *
 * 用户手动切换后存入 localStorage，下次启动优先使用。
 */
import { ref } from 'vue'

const STORAGE_KEY = 'sa-font-scale-v2'   // v2：档位数值已调整，强制重新检测

export const SCALE_LEVELS = {
  small:  1.00,   // 原 medium，适合大屏外接显示器
  medium: 1.15,   // 新默认，常规桌面显示器
  large:  1.32,   // 笔记本 Retina 小屏
}

export const SCALE_LABELS = {
  small:  'A⁻',
  medium: 'A',
  large:  'A⁺',
}

/** 根据屏幕参数自动推断初始档位 */
function autoDetect() {
  const dpr = window.devicePixelRatio || 1
  const sw  = window.screen.width        // CSS 逻辑像素宽度

  // 大尺寸 4K/5K 外接显示器（物理 4K 但系统未开 HiDPI）
  if (sw >= 2560 && dpr <= 1.25) return 'small'

  // Retina 笔记本（MBP 13/14/16、MBA）
  if (dpr >= 1.75 && sw <= 1800) return 'large'

  // 低分辨率小屏笔记本
  if (sw <= 1366) return 'large'

  return 'medium'
}

function applyScale(level) {
  const ratio = SCALE_LEVELS[level] ?? 1
  document.documentElement.style.setProperty('--font-scale', ratio)
}

// ── 单例状态（整个应用共享同一个 ref） ─────────────────────────────
const _level = ref(null)

export function useFontScale() {
  if (_level.value === null) {
    const saved = localStorage.getItem(STORAGE_KEY)
    _level.value = (saved && saved in SCALE_LEVELS) ? saved : autoDetect()
    applyScale(_level.value)
  }

  function setLevel(l) {
    if (!(l in SCALE_LEVELS)) return
    _level.value = l
    localStorage.setItem(STORAGE_KEY, l)
    applyScale(l)
  }

  return {
    level: _level,         // ref<'small'|'medium'|'large'>
    setLevel,
    levels: Object.keys(SCALE_LEVELS),
    labels: SCALE_LABELS,
  }
}
