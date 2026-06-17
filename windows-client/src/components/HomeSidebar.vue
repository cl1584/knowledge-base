<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NScrollbar } from 'naive-ui'
import { useNotesStore } from '@/stores/notes'
import { useChatStore } from '@/stores/chat'
import NoteList from './NoteList.vue'

const notes = useNotesStore()
const chat = useChatStore()
const emit = defineEmits<{
  (e: 'create'): void
  (e: 'openSearch'): void
  (e: 'openTrash'): void
}>()

const searchKeyword = ref('')

const notesCount = computed(() => notes.notes?.length ?? 0)

function toggleTag(tagId: number) {
  notes.toggleTagFilter(tagId)
}
</script>

<template>
  <div class="sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">笔记</span>
      <NButton text @click="emit('create')" title="新建 (Ctrl+N)">
        <template #icon>✚</template>
      </NButton>
    </div>

    <div class="search-box" @click="emit('openSearch')">
      <span>🔍</span>
      <span class="placeholder">搜索</span>
      <span class="kbd">Ctrl K</span>
    </div>

    <!-- AI 入口 -->
    <div class="ai-entry" @click="chat.openPanel()">
      <div class="ai-entry-icon">✨</div>
      <div class="ai-entry-text">
        <div class="ai-entry-title">AI 助手</div>
        <div class="ai-entry-sub">基于你的 {{ notesCount }} 篇笔记</div>
      </div>
      <div class="ai-entry-arrow">›</div>
    </div>

    <!-- 已删除入口 -->
    <div class="trash-entry" @click="emit('openTrash')">
      <span class="trash-icon">🗑️</span>
      <span class="trash-text">已删除</span>
      <span class="trash-count" v-if="(notes?.deletedNotes?.length ?? 0) > 0">{{ notes?.deletedNotes?.length ?? 0 }}</span>
    </div>

    <!-- 标签筛选 -->
    <div v-if="(notes?.allTags?.length ?? 0) > 0" class="tags-filter">
      <div class="tags-filter-header">
        <span>标签</span>
        <span v-if="(notes?.activeTagIds?.length ?? 0) > 0" class="clear-filter" @click="notes?.clearTagFilter?.()">清除</span>
      </div>
      <div class="tag-list">
        <span
          v-for="t in (notes?.allTags ?? [])"
          :key="t.id"
          :class="['tag-chip', { active: (notes?.activeTagIds ?? []).includes(t.id) }]"
          @click="toggleTag(t.id)"
        >
          #{{ t.name }}
          <span class="tag-count">{{ t.note_count || 0 }}</span>
        </span>
      </div>
    </div>

    <NScrollbar class="note-list-scroll">
      <NoteList
        :grouped="notes?.groupedNotes ?? {}"
        :current-id="notes?.currentId ?? null"
        :loading="notes?.loading ?? false"
        :has-more="notes?.hasMore ?? false"
        :keyword="searchKeyword"
        @select="(id) => notes?.selectNote(id)"
        @load-more="notes?.loadMore?.()"
      />
    </NScrollbar>
  </div>
</template>

<style scoped>
.sidebar {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 12px 0;
}
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px 8px;
}
.sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-2, #6e6e73);
}
.search-box {
  margin: 0 12px 8px;
  padding: 6px 10px;
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-soft, #e8e8ec);
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-3, #9a9aa0);
  cursor: pointer;
  font-size: 13px;
  transition: border-color 0.15s, background 0.15s;
}
.search-box:hover { border-color: var(--border, #d8d8dc); }
.kbd {
  margin-left: auto;
  font-size: 11px;
  padding: 1px 5px;
  background: var(--bg-hover, #e3e3e6);
  border-radius: 4px;
  font-family: ui-monospace, monospace;
}
.ai-entry {
  margin: 0 12px 8px;
  padding: 10px 12px;
  background: linear-gradient(135deg, rgba(99, 102, 241, 0.12) 0%, rgba(236, 72, 153, 0.12) 100%);
  border: 1px solid rgba(139, 92, 246, 0.2);
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 10px;
  transition: transform 0.1s, box-shadow 0.15s;
}
.ai-entry:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.2);
}
.ai-entry-icon {
  width: 28px; height: 28px;
  display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%);
  color: white;
  border-radius: 7px;
  font-size: 14px;
  box-shadow: 0 2px 6px rgba(139, 92, 246, 0.4);
}
.ai-entry-text { flex: 1; min-width: 0; }
.ai-entry-title { font-size: 13px; font-weight: 600; }
.ai-entry-sub { font-size: 11px; color: var(--text-2, #6e6e73); margin-top: 1px; }
.ai-entry-arrow { color: var(--text-3, #9a9aa0); }

.trash-entry {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 12px 8px;
  padding: 6px 10px;
  font-size: 13px;
  color: var(--text-2, #6e6e73);
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s;
}
.trash-entry:hover { background: var(--bg-hover, #e3e3e6); }
.trash-icon { font-size: 14px; }
.trash-text { flex: 1; }
.trash-count {
  background: var(--bg-active, #d8d8dc);
  color: var(--text-2, #6e6e73);
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 8px;
}

.tags-filter {
  margin: 0 12px 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border-soft, #e8e8ec);
}
.tags-filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3, #9a9aa0);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 8px 4px 6px;
}
.clear-filter {
  font-size: 11px;
  color: var(--accent, #6366f1);
  cursor: pointer;
  font-weight: 500;
  text-transform: none;
  letter-spacing: 0;
}
.clear-filter:hover { text-decoration: underline; }
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.tag-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  font-size: 12px;
  color: var(--text-2, #6e6e73);
  background: var(--bg-card, #fff);
  border: 1px solid var(--border-soft, #e8e8ec);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.12s;
}
.tag-chip:hover {
  background: var(--bg-hover, #e3e3e6);
}
.tag-chip.active {
  background: linear-gradient(135deg, #6366f1, #8b5cf6);
  color: white;
  border-color: transparent;
}
.tag-count {
  font-size: 10px;
  opacity: 0.7;
}
</style>
