/**
 * TTS 语音合成封装
 * 支持后端 Edge TTS 和浏览器原生 TTS fallback
 */
import { loadSettings } from './useSettings.js'
import { stripMarkdown } from '@/utils/markdown.js'

export function useTTS(options = {}) {
  const { onStateChange } = options

  let currentAudio = null
  let audioContext = null
  let audioAnalyser = null

  function getAudioContext() {
    if (!audioContext) {
      audioContext = new (window.AudioContext || window.webkitAudioContext)()
    }
    return audioContext
  }

  function connectAudioAnalyser(audio) {
    const ctx = getAudioContext()
    if (ctx.state === 'suspended') {
      ctx.resume().catch(() => {})
    }
    if (audioAnalyser) {
      try { audioAnalyser.disconnect() } catch {}
    }
    audioAnalyser = ctx.createAnalyser()
    audioAnalyser.fftSize = 256
    audioAnalyser.smoothingTimeConstant = 0.65
    try {
      const source = ctx.createMediaElementSource(audio)
      source.connect(audioAnalyser)
      audioAnalyser.connect(ctx.destination)
    } catch (e) {
      // 同一 Audio 元素只能连接一次，忽略重复连接错误
    }
  }

  function getAudioVolume() {
    if (!audioAnalyser) return 0
    const data = new Uint8Array(audioAnalyser.frequencyBinCount)
    audioAnalyser.getByteFrequencyData(data)
    let sum = 0
    for (let i = 0; i < data.length; i++) sum += data[i]
    return sum / data.length / 255
  }

  function stopSpeaking() {
    if (currentAudio) {
      currentAudio.pause()
      currentAudio.currentTime = 0
      currentAudio = null
    }
    onStateChange?.('idle')
    if (window.speechSynthesis) window.speechSynthesis.cancel()
  }

  async function speak(rawText) {
    if (!rawText) return
    const settings = loadSettings()
    if (!settings.ttsEnabled) return

    const text = stripMarkdown(rawText)
    console.log('[TTS] speak:', text.slice(0, 30) + (text.length > 30 ? '...' : ''))
    stopSpeaking()

    try {
      const res = await fetch('/api/tts/speech', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          text,
          voice: settings.ttsVoice || 'zh-CN-XiaoxiaoNeural',
          rate: settings.ttsRate || '+0%',
          pitch: settings.ttsPitch || '+0Hz',
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)

      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      currentAudio = new Audio(url)
      connectAudioAnalyser(currentAudio)

      currentAudio.onplay = () => { onStateChange?.('talking') }
      currentAudio.onended = () => {
        onStateChange?.('idle')
        URL.revokeObjectURL(url)
        currentAudio = null
      }
      currentAudio.onerror = () => {
        onStateChange?.('idle')
        URL.revokeObjectURL(url)
        currentAudio = null
        speakNative(text)
      }

      await currentAudio.play()
      return
    } catch (e) {
      console.warn('[TTS] Edge TTS failed, falling back to native:', e)
    }

    speakNative(text)
  }

  function speakNative(text) {
    if (!text || !window.speechSynthesis) return
    const settings = loadSettings()
    if (!settings.ttsEnabled) return

    const utterance = new SpeechSynthesisUtterance(text)
    utterance.lang = 'zh-CN'
    utterance.rate = 1.05
    utterance.pitch = 1.0
    utterance.volume = 1.0

    if (settings.ttsVoiceUri) {
      const voices = window.speechSynthesis.getVoices()
      const voice = voices.find(v => v.voiceURI === settings.ttsVoiceUri)
      if (voice) utterance.voice = voice
    }

    utterance.onstart = () => { onStateChange?.('talking') }
    utterance.onend = () => { onStateChange?.('idle') }
    utterance.onerror = () => { onStateChange?.('idle') }

    window.speechSynthesis.speak(utterance)
  }

  return {
    speak,
    stopSpeaking,
    getAudioVolume,
  }
}
