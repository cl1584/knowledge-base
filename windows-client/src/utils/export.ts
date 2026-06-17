/** 导出工具：Markdown 下载 */

export function downloadFile(filename: string, content: string | Blob, mime = 'text/markdown;charset=utf-8') {
  const blob = content instanceof Blob ? content : new Blob([content], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/** 笔记转 Markdown */
export function noteToMarkdown(note: {
  title: string
  content: string
  tags?: string[]
  created_at: string
  updated_at: string
}): string {
  const lines: string[] = []
  const title = note.title || '未命名笔记'
  lines.push(`# ${title}`)
  lines.push('')
  if (note.tags && note.tags.length > 0) {
    lines.push(`> Tags: ${note.tags.map(t => `\`${t}\``).join(', ')}`)
    lines.push('')
  }
  lines.push(`> 创建：${note.created_at}`)
  lines.push(`> 更新：${note.updated_at}`)
  lines.push('')
  lines.push('---')
  lines.push('')
  lines.push(note.content || '')
  return lines.join('\n')
}

/** 文件名安全化：去掉非法字符，限制长度 */
export function safeFilename(name: string, maxLen = 60): string {
  return name
    .replace(/[\\/:*?"<>|\n\r\t]/g, '_')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, maxLen) || 'untitled'
}
