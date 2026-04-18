'use strict'

/**
 * Electron 主进程
 *
 * 职责：
 *   1. 启动 Flask 后端子进程（开发：python run.py；生产：PyInstaller binary）
 *   2. 轮询 /api/health 等待后端就绪
 *   3. 创建 BrowserWindow，加载前端（开发：Vite :5173；生产：dist/index.html）
 *   4. 应用退出时清理后端子进程
 *   5. 注册原生菜单和 IPC 处理器
 */

const { app, BrowserWindow, Menu, shell, ipcMain, dialog } = require('electron')
const { spawn, execSync } = require('child_process')
const path  = require('path')
const http  = require('http')

// 尽早设置应用名称，确保 macOS 菜单栏左上角显示正确名称
app.setName('大道量化')

// TTS 已由后端 Edge TTS 代理，不再依赖 Chromium Web Speech API
// 保留注释以便将来需要时恢复：
// app.commandLine.appendSwitch('enable-speech-dispatcher')
// app.commandLine.appendSwitch('enable-features', 'WebSpeechAPI')
// app.commandLine.appendSwitch('enable-speech-api')
// if (process.platform === 'darwin') {
//   app.commandLine.appendSwitch('disable-features', 'MuteTTS')
// }

// ── 配置 ──────────────────────────────────────────────────────────────────────
const BACKEND_PORT   = 8888
const VITE_PORT      = 5173
// 明确用 127.0.0.1，避免 macOS 将 localhost 解析为 IPv6 (::1) 导致连接失败
const HEALTH_URL     = `http://127.0.0.1:${BACKEND_PORT}/api/health`
const HEALTH_TIMEOUT = 60000   // 最多等待 60s（首次启动需要加载股票池）
const HEALTH_POLL_MS = 400     // 轮询间隔

// 是否为开发模式（未打包时 app.isPackaged = false）
const isDev = !app.isPackaged

let mainWindow     = null
let backendProcess = null
let viteProcess    = null
let splashWindow   = null


// ── 0a. 检测 Vite 开发服务器是否在运行 ───────────────────────────────────────

function checkViteRunning() {
  return new Promise(resolve => {
    http.get(`http://127.0.0.1:${VITE_PORT}`, res => {
      res.resume()
      resolve(res.statusCode < 500)
    }).on('error', () => resolve(false))
  })
}

// 若 Vite 未运行则自动启动，返回 Promise<void>（等到 Vite 就绪）
function ensureVite() {
  return new Promise(async (resolve) => {
    const alreadyUp = await checkViteRunning()
    if (alreadyUp) { resolve(); return }

    console.log('[vite] 自动启动 Vite dev server…')
    const desktopDir = path.join(__dirname, '..')
    viteProcess = spawn(
      process.platform === 'win32' ? 'npm.cmd' : 'npm',
      ['run', 'dev'],
      { cwd: desktopDir, stdio: 'ignore', detached: false }
    )
    viteProcess.on('error', err => console.error('[vite] 启动失败:', err))

    // 轮询直到 Vite 就绪（最多等 30s）
    const deadline = Date.now() + 30000
    const poll = setInterval(async () => {
      if (await checkViteRunning()) {
        clearInterval(poll)
        console.log('[vite] Vite dev server 已就绪')
        resolve()
      } else if (Date.now() > deadline) {
        clearInterval(poll)
        console.warn('[vite] 等待超时，回落到 Flask')
        resolve()
      }
    }, 500)
  })
}


// ── 0b. 清理残留后端进程（避免 DuckDB 文件锁冲突） ───────────────────────────

function killOldBackend() {
  try {
    if (process.platform === 'win32') {
      execSync(`FOR /F "tokens=5" %P IN ('netstat -ano ^| findstr :${BACKEND_PORT}') DO taskkill /PID %P /F`, { stdio: 'ignore' })
    } else {
      execSync(`lsof -ti tcp:${BACKEND_PORT} | xargs kill -9 2>/dev/null || true`, { stdio: 'ignore', shell: true })
    }
    console.log(`[backend] 已清理端口 ${BACKEND_PORT} 上的残留进程`)
  } catch (_) {
    // 端口未占用，正常情况
  }
}


// ── 1. 启动 Flask 后端 ────────────────────────────────────────────────────────

function startBackend() {
  let bin, args, cwd

  if (isDev) {
    // 开发模式：使用系统 Python
    bin  = 'python'
    // __dirname = desktop/electron/，项目根在上两级
    args = [path.join(__dirname, '../../run.py'), `--port=${BACKEND_PORT}`]
    cwd  = path.join(__dirname, '../..')
  } else {
    // 生产模式：使用 PyInstaller 打出的可执行文件
    const backendDir = path.join(process.resourcesPath, 'backend')
    bin  = path.join(backendDir, process.platform === 'win32' ? 'run.exe' : 'run')
    args = [`--port=${BACKEND_PORT}`]
    cwd  = backendDir
  }

  console.log(`[backend] 启动：${bin} ${args.join(' ')}`)

  // 构建子进程环境：继承父进程变量，但剔除 HTTP 代理设置。
  // Tushare 等金融 API 应直连，不走本地 VPN/代理（否则超时或被拦截）。
  const childEnv = { ...process.env, PYTHONUNBUFFERED: '1' }
  for (const key of ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY', 'all_proxy']) {
    delete childEnv[key]
  }

  backendProcess = spawn(bin, args, {
    cwd,
    stdio: 'pipe',
    // Windows 下需要 shell:true 才能找到 .exe
    shell: process.platform === 'win32' && isDev,
    env: childEnv,
  })

  backendProcess.stdout.on('data', d => process.stdout.write(`[backend] ${d}`))
  backendProcess.stderr.on('data', d => process.stderr.write(`[backend] ${d}`))
  backendProcess.on('exit', (code, signal) => {
    console.log(`[backend] 进程退出 code=${code} signal=${signal}`)
    backendProcess = null
  })
}


// ── 2. 轮询后端健康检查 ───────────────────────────────────────────────────────

function waitForBackend() {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + HEALTH_TIMEOUT

    function poll() {
      http.get(HEALTH_URL, res => {
        if (res.statusCode === 200) {
          console.log('[backend] 就绪 ✓')
          resolve()
        } else {
          retry()
        }
        res.resume()
      }).on('error', () => retry())
    }

    function retry() {
      if (Date.now() >= deadline) {
        reject(new Error(`后端未在 ${HEALTH_TIMEOUT / 1000}s 内就绪`))
      } else {
        setTimeout(poll, HEALTH_POLL_MS)
      }
    }

    poll()
  })
}


// ── 3. 启动页窗口（等待后端期间显示） ─────────────────────────────────────────

function createSplash() {
  splashWindow = new BrowserWindow({
    width:  360,
    height: 240,
    frame:  false,
    resizable:   false,
    alwaysOnTop: true,
    transparent: true,
    webPreferences: { nodeIntegration: false },
  })
  // 加载内嵌 HTML，无需文件
  splashWindow.loadURL(`data:text/html;charset=utf-8,
    <html>
    <body style="margin:0;display:flex;flex-direction:column;align-items:center;
                 justify-content:center;height:100vh;
                 background:rgba(255,255,255,0.95);
                 font-family:-apple-system,sans-serif;border-radius:16px;
                 -webkit-app-region:drag;">
      <div style="font-size:18px;font-weight:600;color:#1c1c1e;margin-bottom:12px;">
        大道量化投研平台
      </div>
      <div style="font-size:13px;color:#8e8e93;">正在启动服务…</div>
      <div style="margin-top:20px;width:160px;height:3px;
                  background:#e5e5ea;border-radius:2px;overflow:hidden;">
        <div style="height:100%;background:#007aff;border-radius:2px;
                    animation:prog 1.2s ease-in-out infinite alternate;"></div>
      </div>
      <style>
        @keyframes prog {
          from { width:20%; margin-left:0; }
          to   { width:60%; margin-left:40%; }
        }
      </style>
    </body>
    </html>
  `)
}


// ── 4. 主窗口 ─────────────────────────────────────────────────────────────────

function createWindow() {
  const iconPath = path.join(__dirname, 'icons',
    process.platform === 'darwin' ? 'icon.icns'
    : process.platform === 'win32' ? 'icon.ico'
    : 'icon.png')

  mainWindow = new BrowserWindow({
    width:   1280,
    height:  800,
    minWidth:  900,
    minHeight: 600,
    show: false,   // 加载完成后再显示，避免白屏闪烁
    icon: iconPath,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    // macOS 交通灯按钮纵向居中在 44px 导航栏内（(44-16)/2 ≈ 14）
    // 横向 16px 与导航栏左侧 padding 对齐
    trafficLightPosition: process.platform === 'darwin' ? { x: 16, y: 14 } : undefined,
    webPreferences: {
      preload:          path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration:  false,
      webSecurity:      true,
    },
  })

  if (isDev) {
    // 自动确保 Vite dev server 已就绪，再加载前端
    ensureVite().then(() => {
      checkViteRunning().then(viteUp => {
        const url = viteUp
          ? `http://127.0.0.1:${VITE_PORT}`
          : `http://127.0.0.1:${BACKEND_PORT}`
        console.log(`[electron] 加载前端：${url}`)
        mainWindow.loadURL(url)
      })
    })
    // DevTools 默认不打开，需要时手动通过菜单「视图→开发者工具」或 Cmd+Option+I 打开
  } else {
    mainWindow.loadFile(path.join(__dirname, '../frontend/dist/index.html'))
  }

  mainWindow.once('ready-to-show', () => {
    if (splashWindow && !splashWindow.isDestroyed()) {
      splashWindow.close()
      splashWindow = null
    }
    mainWindow.show()
    mainWindow.focus()
  })

  mainWindow.on('closed', () => { mainWindow = null })

  // 拦截外部链接，用系统浏览器打开
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    if (url.startsWith('http')) shell.openExternal(url)
    return { action: 'deny' }
  })
}


// ── 5. 原生菜单 ───────────────────────────────────────────────────────────────

function buildMenu() {
  const isMac = process.platform === 'darwin'

  const template = [
    // macOS 专属 App 菜单
    ...(isMac ? [{
      label: app.name,
      submenu: [
        { role: 'about', label: '关于大道量化' },
        { type: 'separator' },
        { role: 'services', label: '服务' },
        { type: 'separator' },
        { role: 'hide', label: '隐藏' },
        { role: 'hideOthers', label: '隐藏其他' },
        { role: 'unhide', label: '全部显示' },
        { type: 'separator' },
        { role: 'quit', label: '退出' },
      ],
    }] : []),
    {
      label: '文件',
      submenu: [
        isMac ? { role: 'close', label: '关闭窗口' } : { role: 'quit', label: '退出' },
      ],
    },
    {
      label: '视图',
      submenu: [
        { role: 'reload',       label: '刷新' },
        { role: 'toggleDevTools', label: '开发者工具' },
        { type: 'separator' },
        { role: 'resetZoom',    label: '实际大小' },
        { role: 'zoomIn',       label: '放大' },
        { role: 'zoomOut',      label: '缩小' },
        { type: 'separator' },
        { role: 'togglefullscreen', label: '全屏' },
      ],
    },
    {
      label: '窗口',
      submenu: [
        { role: 'minimize',  label: '最小化' },
        { role: 'zoom',      label: '缩放' },
        ...(isMac ? [
          { type: 'separator' },
          { role: 'front', label: '全部置于顶层' },
        ] : []),
      ],
    },
  ]

  Menu.setApplicationMenu(Menu.buildFromTemplate(template))
}


// ── 6. IPC 处理器 ─────────────────────────────────────────────────────────────

function registerIpcHandlers() {
  // 打开文件对话框
  ipcMain.handle('dialog:openFile', async (_event, options) => {
    const win = BrowserWindow.getFocusedWindow()
    return dialog.showOpenDialog(win, options)
  })

  // 获取应用版本
  ipcMain.handle('app:getVersion', () => app.getVersion())

  // 在系统浏览器中打开外部链接
  ipcMain.handle('shell:openExternal', (_event, url) => {
    if (url.startsWith('http')) shell.openExternal(url)
  })
}


// ── 7. 应用生命周期 ───────────────────────────────────────────────────────────

app.whenReady().then(async () => {
  // macOS：设置 Dock 图标
  if (process.platform === 'darwin' && app.dock) {
    app.dock.setIcon(path.join(__dirname, 'icons', 'icon.png'))
  }

  buildMenu()
  registerIpcHandlers()

  // 启动前先清理残留进程（避免 DuckDB 文件锁冲突）
  killOldBackend()

  // 开发模式：Vite dev server 已经在运行，无需等待后端（用户手动启动 python run.py）
  // 生产模式：启动 Flask 子进程并等待就绪
  if (!isDev) {
    createSplash()
    startBackend()
    try {
      await waitForBackend()
    } catch (err) {
      console.error(err.message)
      dialog.showErrorBox('后端启动失败', `${err.message}\n\n请检查日志或重启应用。`)
      app.quit()
      return
    }
  } else {
    // 开发模式：启动后端并等待就绪（与生产模式相同的等待逻辑）
    createSplash()
    startBackend()
    try {
      await waitForBackend()
    } catch (err) {
      console.warn(`[dev] 后端未就绪：${err.message}`)
      // dev 模式不强制退出，窗口仍然打开（可能 API 调用会失败，便于调试）
      if (splashWindow && !splashWindow.isDestroyed()) {
        splashWindow.close()
        splashWindow = null
      }
    }
  }

  createWindow()

  app.on('activate', () => {
    // macOS：点击 Dock 图标时恢复窗口
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  // macOS 惯例：关闭所有窗口不退出 App
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  // macOS：退出前隐藏 Dock 图标，防止短暂闪回 Electron 默认图标
  if (process.platform === 'darwin' && app.dock) {
    app.dock.hide()
  }
  // 退出前杀掉 Flask 子进程
  if (backendProcess) {
    console.log('[backend] 正在关闭…')
    backendProcess.kill('SIGTERM')
    backendProcess = null
  }
  // 退出前杀掉 Vite 进程（若是 Electron 自动启动的）
  if (viteProcess) {
    console.log('[vite] 正在关闭…')
    viteProcess.kill('SIGTERM')
    viteProcess = null
  }
})
