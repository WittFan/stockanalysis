/**
 * 开发模式下将 Electron 应用名称改为"大道量化"
 *
 * macOS 菜单栏粗体应用名来自 Electron.app/Contents/Info.plist 的 CFBundleName，
 * 无法通过 app.setName() 修改，需要直接写 plist。
 *
 * 在 npm install 后自动执行（postinstall），也可手动运行：
 *   node scripts/rename-electron.js
 */

'use strict'

const { execSync } = require('child_process')
const path = require('path')
const fs   = require('fs')

const APP_NAME = '大道量化'

// 仅 macOS 需要处理
if (process.platform !== 'darwin') {
  console.log('[rename-electron] 非 macOS，跳过')
  process.exit(0)
}

// electron 模块导出的是可执行文件路径
// 如：.../Electron.app/Contents/MacOS/Electron
// Info.plist 在：.../Electron.app/Contents/Info.plist
let electronExec
try {
  electronExec = require('electron')
} catch {
  console.warn('[rename-electron] electron 模块未安装，跳过')
  process.exit(0)
}

const plistPath = path.join(path.dirname(electronExec), '..', 'Info.plist')

if (!fs.existsSync(plistPath)) {
  console.warn(`[rename-electron] Info.plist 未找到：${plistPath}`)
  process.exit(0)
}

try {
  execSync(`/usr/libexec/PlistBuddy -c "Set :CFBundleName ${APP_NAME}" "${plistPath}"`)
  execSync(`/usr/libexec/PlistBuddy -c "Set :CFBundleDisplayName ${APP_NAME}" "${plistPath}"`)
  console.log(`[rename-electron] ✓ 应用名称已改为「${APP_NAME}」`)
} catch (e) {
  console.warn(`[rename-electron] 修改 Info.plist 失败：${e.message}`)
}
