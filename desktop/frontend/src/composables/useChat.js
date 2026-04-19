/**
 * Agent 对话逻辑封装
 * 包含消息状态管理、流式响应处理、工具调用等
 */
import { ref, computed, nextTick } from 'vue'
import { loadSettings, resolveUrl } from './useSettings.js'

function getTime() {
  const n = new Date()
  return `${n.getHours().toString().padStart(2, '0')}:${n.getMinutes().toString().padStart(2, '0')}`
}

export function fmtJson(obj) {
  try { return JSON.stringify(typeof obj === 'string' ? JSON.parse(obj) : obj, null, 2) }
  catch { return String(obj) }
}

// ── 工具定义 ────────────────────────────────────────────────────────
const toolDefs = [
  {
    name: 'get_current_time',
    icon: '🕐', label: '时间', desc: '获取当前日期时间',
    parameters: { type: 'object', properties: {}, required: [] },
    execute: () => new Date().toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai' }),
  },
  {
    name: 'calculate',
    icon: '🧮', label: '计算', desc: '计算数学表达式',
    parameters: {
      type: 'object',
      properties: { expression: { type: 'string', description: '数学表达式，支持 JS 语法' } },
      required: ['expression'],
    },
    execute: ({ expression }) => {
      try {
        const result = Function('"use strict"; return (' + expression + ')')()
        return `${expression} = ${result}`
      } catch (e) {
        return `计算出错: ${e.message}`
      }
    },
  },
  {
    name: 'get_stock_info',
    icon: '📈', label: '行情', desc: '查询A股股票行情',
    parameters: {
      type: 'object',
      properties: { symbol: { type: 'string', description: '股票代码，如 000001.SZ 或 600519.SH' } },
      required: ['symbol'],
    },
    execute: async ({ symbol }) => {
      try {
        const res = await fetch(`/api/chart/ohlcv?ts_code=${encodeURIComponent(symbol)}&limit=5`)
        if (!res.ok) return `获取 ${symbol} 失败 (${res.status})`
        const data = await res.json()
        if (data.error) return `错误: ${data.error}`
        const rows = data.data?.slice(-3) || []
        if (!rows.length) return `未找到 ${symbol} 数据`
        return rows.map(r => `日期: ${r[0]}  开: ${r[1]}  高: ${r[2]}  低: ${r[3]}  收: ${r[4]}  量: ${r[5]}`).join('\n')
      } catch (e) {
        return `网络错误: ${e.message}`
      }
    },
  },
]

const BACKEND_TOOL_ICONS = {
  query_financial_data: '🗄️',
  screen_stocks: '🔍',
  get_stock_valuation: '📊',
  run_backtest: '⚡',
  generate_chart: '📉',
}

const TOOL_ICONS = {
  ...Object.fromEntries(toolDefs.map(t => [t.name, t.icon])),
  ...BACKEND_TOOL_ICONS,
}
export const toolIcon = name => TOOL_ICONS[name] || '⚙️'

const TOOLS_SCHEMA = toolDefs.map(t => ({
  type: 'function',
  function: { name: t.name, description: t.desc, parameters: t.parameters },
}))

// ── useChat ─────────────────────────────────────────────────────────
export function useChat(options = {}) {
  const { speak, stopSpeaking, onStateChange, messagesRef, inputRef } = options

  const inputText = ref('')
  const isLoading = ref(false)
  const isThinking = ref(false)
  const isStreaming = ref(false)
  const displayMessages = ref([])
  const currentSessionId = ref(localStorage.getItem('agent_session_id') || null)
  let apiMessages = []
  let msgId = 0

  const hasSettings = computed(() => {
    const s = loadSettings()
    return s.provider === 'local_kimi' || !!s.apiKey
  })

  const currentModel = computed(() => {
    const s = loadSettings()
    return s.provider === 'local_kimi' ? 'Kimi CLI' : (s.model || '')
  })

  async function scrollToBottom() {
    await nextTick()
    if (messagesRef?.value) messagesRef.value.scrollTop = messagesRef.value.scrollHeight
  }

  function fillSuggest(s) { inputText.value = s }

  function autoResize(e) {
    const el = e.target
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }

  function clearHistory() {
    displayMessages.value = []
    apiMessages = []
    currentSessionId.value = null
    localStorage.removeItem('agent_session_id')
  }

  function pushAssistant(text) {
    displayMessages.value.push({ id: ++msgId, role: 'assistant', content: text, toolCalls: [], streaming: false, time: getTime() })
    scrollToBottom()
    speak?.(text)
  }

  async function executeTool(name, argsRaw) {
    const tool = toolDefs.find(t => t.name === name)
    if (!tool) return `未找到工具: ${name}`
    try {
      const args = typeof argsRaw === 'string' ? JSON.parse(argsRaw) : argsRaw
      return await tool.execute(args)
    } catch (e) {
      return `工具执行错误: ${e.message}`
    }
  }

  async function callAPIStream(settings) {
    const systemPrompt = settings.systemPrompt ||
      '你是助理小姐，一位温柔聪明、精通量化投资的AI智能体。你可以使用工具来帮助用户。请用中文回复。'

    const assistantMsg = {
      id: ++msgId, role: 'assistant', content: '', toolCalls: [], streaming: true, time: getTime(),
    }
    isThinking.value = false
    isStreaming.value = true
    onStateChange?.('talking')
    displayMessages.value.push(assistantMsg)
    await scrollToBottom()

    let res
    if (settings.provider === 'local_kimi') {
      res = await fetch('/api/assistant/chat', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages, system: systemPrompt }),
      })
    } else {
      const defaultUrl = settings.provider === 'kimi' ? 'https://api.kimi.com/coding/v1' : 'https://api.openai.com/v1'
      const baseUrl = resolveUrl(settings.apiUrl || defaultUrl)
      const model = settings.model || (settings.provider === 'kimi' ? 'kimi-for-coding' : 'gpt-4o')
      const extraHeaders = settings.provider === 'kimi' ? { 'user-agent': 'kimi-cli/1.0.0' } : {}

      res = await fetch(`${baseUrl}/chat/completions`, {
        method: 'POST',
        headers: { 'content-type': 'application/json', authorization: `Bearer ${settings.apiKey}`, ...extraHeaders },
        body: JSON.stringify({
          model, stream: true,
          messages: [{ role: 'system', content: systemPrompt }, ...apiMessages],
          tools: TOOLS_SCHEMA, tool_choice: 'auto', max_tokens: 2048,
        }),
      })
    }

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      assistantMsg.streaming = false
      throw new Error(err?.error?.message || `HTTP ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    const tcAccum = {}

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''
      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const data = line.slice(6).trim()
        if (data === '[DONE]') break
        try {
          const json = JSON.parse(data)
          const delta = json.choices?.[0]?.delta
          if (!delta) continue
          if (delta.content) { assistantMsg.content += delta.content; await scrollToBottom() }
          if (delta.tool_calls) {
            for (const dtc of delta.tool_calls) {
              const idx = dtc.index ?? 0
              if (!tcAccum[idx]) {
                tcAccum[idx] = { id: dtc.id || `tc_${idx}`, name: '', args: '' }
                assistantMsg.toolCalls.push({ id: tcAccum[idx].id, name: '', arguments: '', status: 'running', open: true, result: undefined })
              }
              if (dtc.id) tcAccum[idx].id = dtc.id
              if (dtc.function?.name) { tcAccum[idx].name += dtc.function.name; assistantMsg.toolCalls[idx].name = tcAccum[idx].name }
              if (dtc.function?.arguments) { tcAccum[idx].args += dtc.function.arguments; assistantMsg.toolCalls[idx].arguments = tcAccum[idx].args }
            }
            await scrollToBottom()
          }
        } catch { /* skip */ }
      }
    }

    assistantMsg.streaming = false
    isStreaming.value = false

    const toolCallsForApi = Object.values(tcAccum).map(tc => ({
      id: tc.id, type: 'function', function: { name: tc.name, arguments: tc.args },
    }))
    apiMessages.push({
      role: 'assistant',
      content: assistantMsg.content || null,
      tool_calls: toolCallsForApi.length ? toolCallsForApi : undefined,
    })

    return { content: assistantMsg.content, toolCalls: assistantMsg.toolCalls.length ? assistantMsg.toolCalls : null }
  }

  async function agentLoop(maxRounds) {
    for (let round = 0; round < maxRounds; round++) {
      isThinking.value = true
      onStateChange?.('thinking')

      const result = await callAPIStream(loadSettings())

      if (result.toolCalls?.length) {
        for (const tc of result.toolCalls) {
          const toolResult = await executeTool(tc.name, tc.arguments)
          tc.result = toolResult
          tc.status = 'done'
          apiMessages.push({ role: 'tool', tool_call_id: tc.id, content: String(toolResult) })
        }
        onStateChange?.('thinking')
      } else {
        speak?.(result.content)
        break
      }
    }
  }

  async function sendToBackendAgent(text, settings) {
    const systemPrompt = settings.systemPrompt ||
      '你是助理小姐，一位温柔聪明、精通量化投资的AI智能体。你可以使用工具来帮助用户。请用中文回复。'

    const assistantMsg = {
      id: ++msgId, role: 'assistant', content: '', toolCalls: [], streaming: true, time: getTime(),
    }
    isThinking.value = false
    isStreaming.value = true
    onStateChange?.('talking')
    displayMessages.value.push(assistantMsg)
    await scrollToBottom()

    const body = {
      message: text,
      session_id: currentSessionId.value,
      provider: settings.provider || 'openai',
      api_key: settings.apiKey || '',
      api_url: settings.apiUrl || 'https://api.openai.com/v1',
      model: settings.model || 'gpt-4o-mini',
      system_prompt: systemPrompt,
      max_iterations: 10,
    }

    const res = await fetch('/api/agent/chat', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    })

    if (!res.ok) {
      const err = await res.json().catch(() => ({}))
      assistantMsg.streaming = false
      throw new Error(err?.error || `HTTP ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buf = ''
    const tcIndex = {}

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buf += decoder.decode(value, { stream: true })
      const lines = buf.split('\n')
      buf = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        let event
        try { event = JSON.parse(line.slice(6)) } catch { continue }

        switch (event.type) {
          case 'session':
            currentSessionId.value = event.session_id
            localStorage.setItem('agent_session_id', event.session_id)
            break
          case 'thought':
            assistantMsg.content += event.content
            await scrollToBottom()
            break
          case 'tool_call': {
            const tc = {
              id: event.id,
              name: event.name,
              arguments: typeof event.arguments === 'string' ? event.arguments : JSON.stringify(event.arguments),
              status: 'running',
              open: true,
              result: undefined,
            }
            tcIndex[event.id] = assistantMsg.toolCalls.length
            assistantMsg.toolCalls.push(tc)
            if (!assistantMsg.content) assistantMsg.content = ''
            await scrollToBottom()
            break
          }
          case 'tool_result': {
            const idx = tcIndex[event.id]
            if (idx !== undefined) {
              assistantMsg.toolCalls[idx].result = event.result
              assistantMsg.toolCalls[idx].status = 'done'
            }
            await scrollToBottom()
            break
          }
          case 'final':
            assistantMsg.content = event.content
            assistantMsg.streaming = false
            isStreaming.value = false
            await scrollToBottom()
            speak?.(event.content)
            break
          case 'budget_warning':
            break
          case 'budget_exceeded':
            assistantMsg.content += '\n\n[已达最大工具调用轮次限制]'
            assistantMsg.streaming = false
            isStreaming.value = false
            break
          case 'error':
            assistantMsg.content = `出错了: ${event.message}`
            assistantMsg.streaming = false
            isStreaming.value = false
            break
          case 'done':
            assistantMsg.streaming = false
            isStreaming.value = false
            break
        }
      }
    }

    assistantMsg.streaming = false
    isStreaming.value = false
  }

  async function sendMessage() {
    const text = inputText.value.trim()
    if (!text || isLoading.value) return
    if (!hasSettings.value) {
      pushAssistant('请先在「设置」中配置 API Key 哦~ 🌸')
      return
    }

    stopSpeaking?.()
    displayMessages.value.push({ id: ++msgId, role: 'user', content: text, time: getTime() })
    apiMessages.push({ role: 'user', content: text })
    inputText.value = ''
    if (inputRef?.value) inputRef.value.style.height = 'auto'
    isLoading.value = true
    onStateChange?.('thinking')
    scrollToBottom()

    try {
      const settings = loadSettings()
      if (settings.provider === 'local_kimi') {
        await agentLoop(5)
      } else {
        await sendToBackendAgent(text, settings)
      }
    } catch (e) {
      pushAssistant(`出错了：${e.message}`)
    } finally {
      isLoading.value = false
      isThinking.value = false
      isStreaming.value = false
    }
  }

  return {
    inputText,
    isLoading,
    isThinking,
    isStreaming,
    displayMessages,
    currentSessionId,
    hasSettings,
    currentModel,
    toolDefs,
    toolIcon,
    sendMessage,
    clearHistory,
    fillSuggest,
    scrollToBottom,
    autoResize,
    pushAssistant,
  }
}
