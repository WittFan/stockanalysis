'use strict'

/**
 * Electron Preload 脚本
 *
 * 运行在渲染进程（Vue 页面）的隔离上下文中，
 * 通过 contextBridge 安全地将原生能力暴露给前端。
 *
 * 安全原则：
 *   - contextIsolation: true  —— 渲染进程无法访问 Node.js API
 *   - nodeIntegration: false  —— 完全禁用渲染进程的 Node 环境
 *   - 只暴露白名单内的具名方法，不暴露任意 ipcRenderer
 */

const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {

  /**
   * 打开原生文件选择对话框
   * @param {Electron.OpenDialogOptions} options
   * @returns {Promise<Electron.OpenDialogReturnValue>}
   *
   * 用法（Vue 组件中）：
   *   const result = await window.electronAPI.openFile({
   *     title: '选择股票池文件',
   *     filters: [{ name: 'Excel', extensions: ['xlsx'] }],
   *     properties: ['openFile'],
   *   })
   *   if (!result.canceled) console.log(result.filePaths[0])
   */
  openFile: (options) => ipcRenderer.invoke('dialog:openFile', options),

  /**
   * 获取应用版本号（来自 package.json）
   * @returns {Promise<string>}  例如 "1.0.0"
   */
  getVersion: () => ipcRenderer.invoke('app:getVersion'),

  /**
   * 在系统默认浏览器中打开外部链接
   * @param {string} url
   */
  openExternal: (url) => ipcRenderer.invoke('shell:openExternal', url),

  /**
   * 判断当前是否运行在 Electron 环境中
   * （Web 模式下 window.electronAPI 不存在，可用于条件渲染）
   */
  isElectron: true,
})
