<script setup lang="ts">
import { NButton } from 'naive-ui'
import { useChatStore } from '@/stores/chat'
import ChatMessages from './ChatMessages.vue'
import ChatInput from './ChatInput.vue'

const chat = useChatStore()
</script>

<template>
  <Transition name="slide">
    <div v-if="chat.panelOpen" class="chat-panel">
      <div class="chat-header">
        <div class="chat-title">✨ AI 助手</div>
        <NButton text @click="chat.closePanel()">✕</NButton>
      </div>

      <ChatMessages />
      <ChatInput />
    </div>
  </Transition>
</template>

<style scoped>
.chat-panel {
  position: fixed;
  right: 0; top: 0;
  width: 480px;
  height: 100vh;
  background: var(--bg-card, #fff);
  border-left: 1px solid var(--border, #d8d8dc);
  box-shadow: -8px 0 24px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  z-index: 100;
}
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border-soft, #e8e8ec);
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.06) 0%, rgba(236, 72, 153, 0.06) 100%);
}
.chat-title {
  font-size: 15px;
  font-weight: 600;
  color: #6366f1;
}
.slide-enter-active, .slide-leave-active {
  transition: transform 0.25s ease;
}
.slide-enter-from, .slide-leave-to {
  transform: translateX(100%);
}
</style>
