<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { NSpin, NEmpty, NText } from 'naive-ui'
import type { Note } from '@/api/notes'

const props = defineProps<{
  grouped: Record<string, Note[]>
  currentId: number | null
  loading: boolean
  hasMore: boolean
  keyword?: string
}>()

const emit = defineEmits<{
  (e: 'select', id: number): void
  (e: 'load-more'): void
}>()

const scrollRef = ref<HTMLElement | null>(null)

function onScroll() {
  const el = scrollRef.value
  if (!el || !props.hasMore || props.loading) return
  if (el.scrollHeight - el.scrollTop - el.clientHeight < 120) {
    emit('load-more')
  }
}

onMounted(() => {
  scrollRef.value?.addEventListener('scroll', onScroll, { passive: true })
})
onUnmounted(() => {
  scrollRef.value?.removeEventListener('scroll', onScroll)
})

function formatTime(iso: string): string {
  const d = new Date(iso)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function highlight(text: string, kw: string): string {
  if (!kw || !text) return text || ''
  const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  return text.replace(new RegExp(escaped, 'gi'), (m) => `<mark>${m}</mark>`)
}

function safeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

const groupEntries = () => Object.entries(props.grouped)
</script>

<template>
  <div ref="scrollRef" class="note-list">
    <NSpin v-if="loading && groupEntries().length === 0" style="padding: 24px; display:flex; justify-content:center" />
    <NEmpty
      v-else-if="groupEntries().length === 0"
      description="还没有笔记"
      size="small"
      style="padding: 24px 8px"
    />
    <template v-else>
      <template v-for="[groupName, groupNotes] in groupEntries()" :key="groupName">
        <div class="date-group">{{ groupName }}</div>
        <div
          v-for="note in groupNotes"
          :key="note.id"
          :data-id="note.id"
          class="note-item"
          :class="{ active: note.id === currentId }"
          @click="emit('select', note.id)"
        >
          <div class="note-title" v-html="highlight(safeHtml(note.title || '未命名笔记'), keyword || '')"></div>
          <div class="note-preview" v-html="highlight(safeHtml((note.content || '').slice(0, 60) || '无内容'), keyword || '')"></div>
          <div class="note-meta">{{ formatTime(note.created_at) }}</div>
        </div>
      </template>

      <!-- 底部加载更多指示器 -->
      <div class="load-more">
        <NSpin v-if="loading" size="small" />
        <NText v-else-if="hasMore" depth="3" class="load-more-text">滚动加载更多</NText>
        <NText v-else depth="3" class="load-more-text">— 已加载全部 —</NText>
      </div>
    </template>
  </div>
</template>

<style scoped>
.note-list {
  padding: 4px 8px 12px;
  height: 100%;
  overflow-y: auto;
  overflow-x: hidden;
}
.date-group {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3, #9a9aa0);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 12px 8px 4px;
}
.note-item {
  padding: 8px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.note-item:hover { background: var(--bg-hover, #e3e3e6); }
.note-item.active { background: var(--bg-active, #d8d8dc); }
.note-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--text, #1d1d1f);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.note-preview {
  font-size: 12px;
  color: var(--text-2, #6e6e73);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.note-meta {
  font-size: 11px;
  color: var(--text-3, #9a9aa0);
  margin-top: 2px;
}
.load-more {
  display: flex;
  justify-content: center;
  padding: 12px 8px;
}
.load-more-text {
  font-size: 11px;
}
:deep(mark) {
  background: rgba(99, 102, 241, 0.18);
  color: #6366f1;
  padding: 0 2px;
  border-radius: 2px;
  font-weight: 600;
}
</style>
