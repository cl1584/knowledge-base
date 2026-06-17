/** Chat API (流式 SSE) */
import { useAuthStore } from '@/stores/auth'
import { getApiBase } from './index'

export interface ChatReference {
  note_id: number
  title: string
  content: string
  score: number
}

export interface ChatChunk {
  type: 'start' | 'delta' | 'done' | 'error'
  content?: string
  references?: ChatReference[]
  is_demo?: boolean
  error?: string
}

const API_BASE = getApiBase()  // legacy, kept for backward compat

export const chatApi = {
  /**
   * 流式问答：onChunk 回调每个 chunk
   * 返回 EventSource
   */
  stream(
    question: string,
    onChunk: (chunk: ChatChunk) => void,
    onDone?: () => void,
    onError?: (err: Error) => void,
  ): () => void {
    const auth = useAuthStore()
    const controller = new AbortController()

    fetch(`${getApiBase()}/api/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
      },
      body: JSON.stringify({ question, top_k: 8 }),
      signal: controller.signal,
    })
      .then(async (resp) => {
        if (!resp.ok || !resp.body) {
          throw new Error(`HTTP ${resp.status}`)
        }
        const reader = resp.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buffer += decoder.decode(value, { stream: true })
          // SSE 事件以 \n\n 分隔；每条事件可含多行 (event: / data: / id: / retry:)
          const events = buffer.split('\n\n')
          buffer = events.pop() || ''
          for (const raw of events) {
            // 拆行处理，支持 event:xxx / data:xxx / 注释行
            const lines = raw.split('\n')
            const dataLines: string[] = []
            for (const line of lines) {
              const trimmed = line.trim()
              if (!trimmed || trimmed.startsWith(':')) continue  // 空行 / 注释
              if (trimmed.startsWith('data:')) {
                dataLines.push(trimmed.slice(5).trimStart())
              }
              // 其他字段 (event: / id: / retry:) 当前不需要，跳过
            }
            const payload = dataLines.join('\n')
            if (!payload) continue
            try {
              const chunk: ChatChunk = JSON.parse(payload)
              onChunk(chunk)
            } catch (e) {
              console.warn('Failed to parse SSE chunk:', payload, e)
            }
          }
        }
        onDone?.()
      })
      .catch((err) => {
        if (err.name !== 'AbortError') onError?.(err)
      })

    return () => controller.abort()
  },

  history: () =>
    fetch(`${getApiBase()}/api/chat/history?limit=50`, {
      headers: { Authorization: `Bearer ${useAuthStore().token}` },
    }).then(r => r.json()),
}
