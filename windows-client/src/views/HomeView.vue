<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { useNotesStore } from '@/stores/notes'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useChatStore } from '@/stores/chat'
import {
  NLayout, NLayoutHeader, NLayoutSider, NLayoutContent,
  NButton, NInput, NEmpty, NDropdown, NModal, NList, NListItem, NThing,
  useMessage, useDialog,
} from 'naive-ui'
import { noteToMarkdown, downloadFile } from '@/utils/export'

import HomeSidebar from '@/components/HomeSidebar.vue'
import NoteEditor from '@/components/NoteEditor.vue'
import ChatPanel from '@/components/ChatPanel.vue'
import SettingsDrawer from '@/components/SettingsDrawer.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

const notes = useNotesStore()
const auth = useAuthStore()
const settings = useSettingsStore()
const chat = useChatStore()
const message = useMessage()
const dialog = useDialog()

const searchOpen = ref(false)
const searchKeyword = ref('')
const settingsOpen = ref(false)
const trashOpen = ref(false)

const topbarMenu = [
  { label: '设置', key: 'settings' },
  { label: '已删除', key: 'trash' },
  { type: 'divider', key: 'd1' },
  { label: '登出', key: 'logout' },
]

const aiStatusText = computed(() => {
  if (chat?.isDemo === true) return 'AI 演示'
  if (chat?.isDemo === false) return 'AI 已连接'
  return 'AI 待连接'
})
const aiStatusColor = computed(() => {
  if (chat?.isDemo === true) return '#ff9500'
  if (chat?.isDemo === false) return '#8b5cf6'
  return 'var(--text-3, #9a9aa0)'
})

// 笔记数：computed 保护（HMR 边界情况 + 任何 store 异常都不会让整页崩）
const notesCount = computed(() => notes?.notes?.length ?? 0)
const tagsCount = computed(() => notes?.allTags?.length ?? 0)

function handleMenu(key: string) {
  if (key === 'settings') settingsOpen.value = true
  else if (key === 'trash') openTrash()
  else if (key === 'logout') handleLogout()
}

onMounted(async () => {
  try {
    await notes.fetchList()
    await notes.fetchAllTags()
  } catch (e: any) {
    message.error('加载笔记失败：' + (e.response?.data?.detail || e.message))
  }
  // 监听全局快捷键
  window.addEventListener('keydown', handleGlobalKeydown)
  window.addEventListener('kb:open-search', () => {
    searchOpen.value = true
  })
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleGlobalKeydown)
})

async function openTrash() {
  await notes.fetchDeleted()
  trashOpen.value = true
}

async function handleCreate() {
  try {
    await notes.createNote()
  } catch (e: any) {
    message.error('创建失败：' + (e.response?.data?.detail || e.message))
  }
}

function handleSelectNote(id: number) {
  notes.selectNote(id)
}

async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    await notes.fetchList()
  } else {
    await notes.search(searchKeyword.value.trim())
  }
  searchOpen.value = false
}

async function handleRestore(id: number) {
  try {
    await notes.restoreNote(id)
    message.success('已恢复')
  } catch (e: any) {
    message.error('恢复失败：' + (e.response?.data?.detail || e.message))
  }
}

async function handlePermanentDelete(id: number) {
  dialog.warning({
    title: '永久删除',
    content: '此操作不可恢复，确定永久删除？',
    positiveText: '永久删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await notes.deleteNote(id, true)
        message.success('已永久删除')
      } catch (e: any) {
        message.error('删除失败')
      }
    },
  })
}

async function handleLogout() {
  dialog.warning({
    title: '确认登出',
    content: '登出后需要重新输入密码',
    positiveText: '登出',
    negativeText: '取消',
    onPositiveClick: () => {
      auth.logout()
      message.success('已登出')
    },
  })
}

function handleGlobalKeydown(e: KeyboardEvent) {
  // 忽略输入框里的快捷键
  const tag = (e.target as HTMLElement)?.tagName
  if (tag === 'INPUT' || tag === 'TEXTAREA') return
  if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
    e.preventDefault()
    handleCreate()
  } else if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
    e.preventDefault()
    searchOpen.value = true
  }
}

function cycleTheme() {
  const order = ['light', 'dark', 'cyber'] as const
  const idx = order.indexOf(settings.theme)
  const next = order[(idx + 1) % order.length]
  settings.setTheme(next)
  message.info('切换到 ' + (next === 'cyber' ? '⚡ 赛博' : next === 'dark' ? '🌙 深色' : '☀️ 浅色') + ' 主题')
}

function handleExportAll() {
  const list = notes?.notes ?? []
  if (list.length === 0) {
    message.warning('没有可导出的笔记')
    return
  }
  const parts: any[] = []
  parts.push('# 知识库导出')
  parts.push('')
  parts.push('> 共 ' + list.length + ' 篇笔记')
  parts.push('> 导出时间：' + new Date().toLocaleString('zh-CN'))
  parts.push('> 提示：批量导出不含标签信息，如需标签请单篇导出')
  parts.push('')
  parts.push('---')
  parts.push('')
  for (const n of list) {
    parts.push(noteToMarkdown({
      title: n.title || '未命名笔记',
      content: n.content || '',
      // 批量导出时 notes 列表不含 tags（tags 需单独请求），此处留空
      // 如需标签，可在后端 /api/notes 接口里 join tags 后一并返回
      tags: [],
      created_at: n.created_at,
      updated_at: n.updated_at,
    }))
    parts.push('')
    parts.push('---')
    parts.push('')
  }
  const date = new Date().toISOString().slice(0, 10)
  downloadFile('知识库-' + date + '.md', parts.join('\n'))
  message.success('已导出 ' + list.length + ' 篇')
}
</script>

<template>
  <NLayout has-sider class="home-layout">
    <!-- Sidebar -->
    <NLayoutSider :width="280" :native-scrollbar="false" bordered>
      <HomeSidebar
        @create="handleCreate"
        @open-search="searchOpen = true"
        @open-trash="openTrash"
      />
    </NLayoutSider>

    <!-- Main -->
    <NLayout>
      <NLayoutHeader bordered class="topbar">
        <div class="topbar-left">
          <span class="topbar-title">知识库</span>
        </div>
        <div class="topbar-right">
          <NButton text @click="chat.openPanel()" type="primary" class="ai-top-btn">
            ✨ AI 助手
          </NButton>
          <NButton text @click="cycleTheme">🌗</NButton>
          <NDropdown :options="topbarMenu" @select="handleMenu">
            <NButton text>⚙️</NButton>
          </NDropdown>
        </div>
      </NLayoutHeader>

      <NLayoutContent class="content-area">
        <ErrorBoundary fallback-title="笔记编辑器出错">
          <NoteEditor v-if="notes.current" :note="notes.current" />
          <NEmpty v-else description="还没有笔记，点击 ✚ 创建一条吧" class="empty-state">
            <template #extra>
              <NButton type="primary" @click="handleCreate">✚ 新建笔记</NButton>
            </template>
          </NEmpty>
        </ErrorBoundary>
      </NLayoutContent>
    </NLayout>
  </NLayout>

  <!-- AI 面板 -->
  <ErrorBoundary fallback-title="AI 面板出错">
    <ChatPanel />
  </ErrorBoundary>

  <!-- 搜索弹窗 -->
  <NModal v-model:show="searchOpen" :mask-closable="true" preset="card" style="max-width: 600px" :bordered="false">
    <NInput
      v-model:value="searchKeyword"
      placeholder="搜索笔记..."
      size="large"
      autofocus
      @keydown.enter="handleSearch"
    />
  </NModal>

  <!-- 已删除笔记 -->
  <NModal v-model:show="trashOpen" preset="card" style="max-width: 600px" :bordered="false" title="已删除笔记（30 天内可恢复）">
    <NEmpty
      v-if="(notes?.deletedNotes?.length ?? 0) === 0"
      description="没有已删除的笔记"
    />
    <NList v-else>
      <NListItem v-for="note in (notes?.deletedNotes ?? [])" :key="note.id">
        <NThing>
          <template #header>{{ note.title || '未命名笔记' }}</template>
          <template #description>
            <span style="font-size: 12px; color: var(--text-3)">
              {{ new Date(note.updated_at).toLocaleString('zh-CN') }} · {{ (note.content || '').slice(0, 40) }}
            </span>
          </template>
        </NThing>
        <template #suffix>
          <NButton size="small" type="primary" @click="handleRestore(note.id)">恢复</NButton>
          <NButton size="small" type="error" ghost @click="handlePermanentDelete(note.id)">永久删</NButton>
        </template>
      </NListItem>
    </NList>
  </NModal>

  <!-- 设置抽屉 -->
  <SettingsDrawer v-model:show="settingsOpen" />

  <!-- Status bar -->
  <div class="statusbar">
    <div class="status-left">
      <span class="status-item">{{ notesCount }} 篇</span>
      <span class="status-item" v-if="tagsCount > 0">{{ tagsCount }} 标签</span>
      <span class="status-item" :style="{ color: aiStatusColor }">● {{ aiStatusText }}</span>
    </div>
    <div class="status-right">
      <span class="status-item clickable" @click="handleExportAll">📥 导出全部</span>
      <span class="status-item">v0.1.0</span>
    </div>
  </div>
</template>

<style scoped>
.home-layout {
  height: 100vh;
}
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
}
.kbd {
  margin-left: auto;
  font-size: 11px;
  padding: 1px 5px;
  background: var(--bg-hover, #e3e3e6);
  border-radius: 4px;
  font-family: ui-monospace, monospace;
}
.ai-entry {
  margin: 0 12px 12px;
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

.note-list-scroll { flex: 1; }

.topbar {
  height: 48px;
  padding: 0 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.topbar-title {
  font-weight: 600;
  font-size: 14px;
}
.topbar-right {
  display: flex;
  gap: 8px;
  align-items: center;
}
.ai-top-btn {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%) !important;
  color: white !important;
  font-weight: 600 !important;
  padding: 4px 12px !important;
  border-radius: 6px !important;
  box-shadow: 0 2px 8px rgba(139, 92, 246, 0.35);
}
.content-area {
  height: calc(100vh - 48px - 28px);
  overflow: auto;
}
.empty-state {
  margin-top: 120px;
}

/* Status bar */
.statusbar {
  position: fixed;
  bottom: 0; left: 0; right: 0;
  height: 28px;
  background: var(--bg-sidebar, #ececef);
  border-top: 1px solid var(--border-soft, #e8e8ec);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 14px;
  color: var(--text-3, #9a9aa0);
  font-size: 11px;
  z-index: 10;
}
.statusbar .status-left,
.statusbar .status-right {
  display: flex;
  align-items: center;
  gap: 14px;
}
.statusbar .status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.statusbar .clickable {
  cursor: pointer;
  padding: 2px 8px;
  border-radius: 4px;
  transition: background 0.12s;
}
.statusbar .clickable:hover {
  background: var(--bg-hover, #e3e3e6);
  color: var(--accent, #6366f1);
}
</style>
