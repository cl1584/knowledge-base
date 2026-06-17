<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { NEmpty, NScrollbar } from 'naive-ui'
import { useChatStore } from '@/stores/chat'
import { useNotesStore } from '@/stores/notes'

const chat = useChatStore()
const notes = useNotesStore()
const messagesScrollRef = ref<InstanceType<typeof NScrollbar> | null>(null)

function openNote(noteId: number) {
  notes.selectNote(noteId)
  chat.closePanel()
  setTimeout(() => {
    const el = document.querySelector(`.note-item[data-id="${noteId}"]`) as HTMLElement | null
    if (el) {
      el.classList.remove('flash-highlight')
      void el.offsetWidth
      requestAnimationFrame(() => {
        el.classList.add('flash-highlight')
      })
    }
  }, 350)
}

// 消息变化时滚到底部
watch(() => chat.messages.length, () => {
  nextTick(() => {
    messagesScrollRef.value?.scrollTo({ top: 999999 })
  })
})

// 内容变化（流式）也滚
watch(() => chat.messages[chat.messages.length - 1]?.content, () => {
  nextTick(() => {
    messagesScrollRef.value?.scrollTo({ top: 999999 })
  })
})
</script>

<template>
  <NScrollbar ref="messagesScrollRef" class="chat-messages">
    <NEmpty
      v-if="chat.messages.length === 0"
      description="开始和你的知识库对话吧"
      size="small"
      style="margin-top: 80px"
    />
    <div
      v-for="msg in chat.messages"
      :key="msg.id"
      :class="['msg', msg.role]"
    >
      <div class="msg-bubble">
        <div v-if="msg.thinking" class="thinking">
          <span></span><span></span><span></span>
        </div>
        <template v-else>{{ msg.content }}</template>

        <div v-if="msg.isDemo" class="demo-badge">⚠️ 演示模式（未配 DEEPSEEK_API_KEY）</div>

        <div v-if="msg.references && msg.references.length" class="references">
          <div class="ref-label">📎 引用了 {{ msg.references.length }} 篇笔记：</div>
          <div
            v-for="ref in msg.references"
            :key="ref.note_id"
            class="ref-card"
            @click="openNote(ref.note_id)"
          >
            <span class="ref-icon">📄</span>
            <span class="ref-title">{{ ref.title }}</span>
            <span class="ref-score">{{ (ref.score * 100).toFixed(0) }}%</span>
          </div>
        </div>
      </div>
    </div>
  </NScrollbar>
</template>

<style scoped>
.chat-messages {
  flex: 1;
  padding: 18px;
}
.msg {
  display: flex;
  flex-direction: column;
  margin-bottom: 14px;
  max-width: 85%;
}
.msg.user { align-self: flex-end; align-items: flex-end; }
.msg.assistant { align-self: flex-start; }
.msg-bubble {
  padding: 10px 14px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-word;
}
.msg.user .msg-bubble {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
  color: white;
  border-bottom-right-radius: 4px;
}
.msg.assistant .msg-bubble {
  background: var(--bg-hover, #e3e3e6);
  color: var(--text, #1d1d1f);
  border-bottom-left-radius: 4px;
}
.thinking {
  display: inline-flex;
  gap: 4px;
  padding: 4px 0;
}
.thinking span {
  width: 6px; height: 6px;
  background: currentColor;
  border-radius: 50%;
  animation: thinking 1.4s ease-in-out infinite;
}
.thinking span:nth-child(2) { animation-delay: 0.2s; }
.thinking span:nth-child(3) { animation-delay: 0.4s; }
@keyframes thinking {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.3; }
  30% { transform: translateY(-6px); opacity: 1; }
}
.demo-badge {
  margin-top: 8px;
  padding: 4px 8px;
  font-size: 11px;
  color: #ff9500;
  background: rgba(255, 149, 0, 0.1);
  border: 1px solid rgba(255, 149, 0, 0.3);
  border-radius: 4px;
  display: inline-block;
}
.references {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-soft, #e8e8ec);
}
.ref-label {
  font-size: 11px;
  color: var(--text-3, #9a9aa0);
  margin-bottom: 6px;
}
.ref-card {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  margin-top: 4px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-soft, #e8e8ec);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s;
  font-size: 12px;
}
.ref-card:hover {
  border-color: #8b5cf6;
  background: rgba(139, 92, 246, 0.08);
}
.ref-icon { color: #8b5cf6; }
.ref-title { flex: 1; font-weight: 500; }
.ref-score { color: var(--text-3, #9a9aa0); font-size: 10px; }
</style>
