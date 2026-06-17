<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { NInput, NButton } from 'naive-ui'
import { useChatStore } from '@/stores/chat'

const chat = useChatStore()
const inputText = ref('')
const inputRef = ref<InstanceType<typeof NInput> | null>(null)

watch(() => chat.panelOpen, (open) => {
  if (open) {
    nextTick(() => inputRef.value?.focus())
  }
})

function send() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  chat.ask(text)
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    send()
  }
}
</script>

<template>
  <div class="chat-input-area">
    <div class="chat-input-box">
      <NInput
        ref="inputRef"
        v-model:value="inputText"
        type="textarea"
        :autosize="{ minRows: 1, maxRows: 4 }"
        placeholder="问问你的知识库..."
        @keydown="handleKeydown"
      />
      <NButton
        class="send-btn"
        :disabled="!inputText.trim() || chat.streaming"
        @click="send"
      >
        ➤
      </NButton>
    </div>
    <div class="chat-tip">基于你的全部笔记 · DeepSeek 驱动 · 按 Enter 发送</div>
  </div>
</template>

<style scoped>
.chat-input-area {
  padding: 14px 18px;
  border-top: 1px solid var(--border-soft, #e8e8ec);
}
.chat-input-box {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 8px 12px;
  background: transparent;
  border: 1px solid var(--border-soft, #e8e8ec);
  border-radius: 12px;
  transition: border-color 0.15s, background 0.15s;
}
.chat-input-box:focus-within {
  border-color: rgba(99, 102, 241, 0.4);
  background: var(--bg-hover, #e3e3e6);
}
.chat-input-box :deep(.n-input),
.chat-input-box :deep(.n-input__wrapper) {
  background: transparent !important;
  box-shadow: none !important;
}
.chat-input-box :deep(textarea) {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif !important;
  font-size: 14px !important;
  line-height: 1.6 !important;
  color: var(--text, #1d1d1f) !important;
  font-weight: 400 !important;
  letter-spacing: 0 !important;
  -webkit-font-smoothing: antialiased !important;
  -moz-osx-font-smoothing: grayscale !important;
  background: transparent !important;
  caret-color: #6366f1;
}
.chat-input-box :deep(textarea::placeholder) {
  color: var(--text-3, #9a9aa0) !important;
  opacity: 0.8;
}
.send-btn {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%) !important;
  color: white !important;
  border: none !important;
  font-weight: 600 !important;
  width: 32px;
  height: 32px;
  padding: 0 !important;
}
.chat-tip {
  font-size: 11px;
  color: var(--text-3, #9a9aa0);
  margin-top: 6px;
  text-align: center;
}
</style>
