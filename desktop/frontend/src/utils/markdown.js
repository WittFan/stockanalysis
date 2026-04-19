/**
 * Markdown 处理工具
 */

export function md(text) {
  if (!text) return ''
  let s = text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  s = s.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
    `<pre class="md-pre"><code class="md-code">${code.trim()}</code></pre>`)
  s = s.replace(/`([^`\n]+)`/g, '<code class="md-inline">$1</code>')
  s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
  s = s.replace(/\*(.*?)\*/g, '<em>$1</em>')
  s = s.replace(/^### (.+)$/gm, '<h3 class="md-h">$1</h3>')
  s = s.replace(/^## (.+)$/gm, '<h2 class="md-h">$1</h2>')
  s = s.replace(/^# (.+)$/gm, '<h1 class="md-h">$1</h1>')
  s = s.replace(/^[-*] (.+)$/gm, '<li>$1</li>')
  s = s.replace(/\n\n/g, '<br><br>').replace(/\n/g, '<br>')
  return s
}

export function stripMarkdown(text) {
  if (!text) return ''
  return text
    .replace(/```[\s\S]*?```/g, '（代码省略）')
    .replace(/`([^`\n]+)`/g, '$1')
    .replace(/\*\*([^*]+)\*\*/g, '$1')
    .replace(/\*([^*]+)\*/g, '$1')
    .replace(/~~([^~]+)~~/g, '$1')
    .replace(/^#{1,6}\s+/gm, '')
    .replace(/^\s*[-*]\s+/gm, '')
    .replace(/^\s*\d+\.\s+/gm, '')
    .replace(/!\[([^\]]*)\]\([^)]+\)/g, '$1')
    .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
    .replace(/^>\s+/gm, '')
    .replace(/^---+$/gm, '')
    .replace(/\$([^$\n]+)\$/g, '$1')
    .replace(/\$\$[\s\S]*?\$\$/g, '（公式省略）')
    .replace(/https?:\/\/\S+/g, '（链接）')
    .replace(/\p{Extended_Pictographic}/gu, '')
    .replace(/\n+/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}
