/** Chat Store：AI 对话历史 + 当前会话 */
import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { chatApi, type ChatReference } from '@/api/chat'

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  references?: ChatReference[]
  isDemo?: boolean
  thinking?: boolean
  createdAt: number
}

const STORAGE_KEY = 'kb-chat-history'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>(loadFromStorage())
  const streaming = ref(false)
  const panelOpen = ref(false)
  const isDemo = ref<boolean | null>(null)  // null=未知, true=演示, false=真实
  // 当前请求的 abort 函数（关面板时调用）—— 必须在 setup 顶部声明，避免 TDZ
  let currentStop: (() => void) | null = null

  // 持久化：thinking 状态不存；保留最近 30 条
  // 流式输出期间（streaming=true）跳过，避免每个 token 都写 localStorage
  function persist() {
    try {
      const slim = messages.value.filter(m => !m.thinking).slice(-30)
      localStorage.setItem(STORAGE_KEY, JSON.stringify(slim))
    } catch {}
  }

  watch(messages, () => {
    if (!streaming.value) persist()
  }, { deep: true })

  // 流式结束后补一次持久化（关闭面板时也够用）
  watch(streaming, (val) => {
    if (!val) persist()
  })

  function addMessage(msg: Omit<ChatMessage, 'id' | 'createdAt'>) {
    const id = Math.random().toString(36).slice(2)
    messages.value.push({ ...msg, id, createdAt: Date.now() })
    return id
  }

  function updateMessage(id: string, patch: Partial<ChatMessage>) {
    const m = messages.value.find(x => x.id === id)
    if (m) Object.assign(m, patch)
  }

  function appendDelta(id: string, delta: string) {
    const m = messages.value.find(x => x.id === id)
    if (m) m.content += delta
  }

  async function ask(question: string) {
    if (streaming.value) return
    panelOpen.value = true
    addMessage({ role: 'user', content: question })

    const assistantId = addMessage({ role: 'assistant', content: '', thinking: true })
    streaming.value = true

    const stop = chatApi.stream(
      question,
      (chunk) => {
        if (chunk.type === 'start') {
          isDemo.value = chunk.is_demo ?? null
          updateMessage(assistantId, {
            thinking: false,
            references: chunk.references,
            isDemo: chunk.is_demo,
          })
        } else if (chunk.type === 'delta' && chunk.content) {
          const m = messages.value.find(x => x.id === assistantId)
          if (m?.thinking) updateMessage(assistantId, { thinking: false })
          appendDelta(assistantId, chunk.content)
        } else if (chunk.type === 'error') {
          updateMessage(assistantId, { content: `错误：${chunk.error}`, thinking: false })
        }
      },
      () => {
        streaming.value = false
      },
      (err) => {
        updateMessage(assistantId, { content: `网络错误：${err.message}`, thinking: false })
        streaming.value = false
      },
    )

    currentStop = stop || null
    return stop
  }

  function clear() {
    messages.value = []
  }

  function openPanel() { panelOpen.value = true }

  function closePanel() {
    // 关面板时取消正在进行的请求
    if (currentStop) {
      currentStop()
      currentStop = null
      streaming.value = false
    }
    panelOpen.value = false
  }
  function togglePanel() { panelOpen.value = !panelOpen.value }

  return {
    messages, streaming, panelOpen, isDemo,
    ask, clear, addMessage, updateMessage,
    openPanel, closePanel, togglePanel,
  }
})

function loadFromStorage(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw)
  } catch {}
  return []
}
