<script setup lang="ts">
import { NModal } from 'naive-ui'

defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

const shortcuts = [
  { key: '?', desc: '打开这个帮助' },
  { key: 'Ctrl + N', desc: '新建笔记' },
  { key: 'Ctrl + S', desc: '保存当前笔记' },
  { key: 'Ctrl + K', desc: '搜索笔记' },
  { key: 'Esc', desc: '关闭弹窗 / AI 面板' },
  { key: 'Enter', desc: '在 AI 面板发送消息（Shift+Enter 换行）' },
  { key: '点 AI 引用卡', desc: '跳转到对应笔记' },
  { key: '点标签', desc: '筛选带该标签的笔记' },
]
</script>

<template>
  <NModal
    :show="show"
    preset="card"
    style="max-width: 480px"
    :bordered="false"
    title="⌨️ 快捷键"
    @update:show="emit('update:show', $event)"
  >
    <div class="shortcuts-list">
      <div v-for="s in shortcuts" :key="s.key" class="shortcut-row">
        <kbd class="kbd">{{ s.key }}</kbd>
        <span class="desc">{{ s.desc }}</span>
      </div>
    </div>
    <p class="hint">按 <kbd>?</kbd> 或 <kbd>Esc</kbd> 关闭</p>
  </NModal>
</template>

<style scoped>
.shortcuts-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.shortcut-row {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 6px 0;
}
.kbd {
  display: inline-block;
  min-width: 100px;
  padding: 4px 10px;
  font-family: ui-monospace, monospace;
  font-size: 12px;
  background: var(--bg-hover, #e3e3e6);
  color: var(--text, #1d1d1f);
  border: 1px solid var(--border-soft, #e8e8ec);
  border-bottom-width: 2px;
  border-radius: 4px;
  text-align: center;
}
.desc {
  font-size: 13px;
  color: var(--text-2, #6e6e73);
  flex: 1;
}
.hint {
  text-align: center;
  font-size: 12px;
  color: var(--text-3, #9a9aa0);
  margin: 16px 0 0;
}
.hint .kbd {
  min-width: auto;
  padding: 1px 6px;
  font-size: 11px;
}
</style>
