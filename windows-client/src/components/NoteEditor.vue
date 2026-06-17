<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, computed } from 'vue'
import { NInput, NButton, NTag, NSpace, useMessage, useDialog } from 'naive-ui'
import type { Note } from '@/api/notes'
import { useNotesStore } from '@/stores/notes'
import { useChatStore } from '@/stores/chat'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { noteToMarkdown, downloadFile, safeFilename } from '@/utils/export'

const props = defineProps<{ note: Note }>()
const notes = useNotesStore()
const chat = useChatStore()
const message = useMessage()
const dialog = useDialog()

const title = ref(props.note.title)
const content = ref(props.note.content)
const previewMode = ref(false)
const saveStatus = ref<'saved' | 'saving' | 'dirty'>('saved')
const newTagInput = ref('')
const newTagShowInput = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | null = null
let lastSavedContent = props.note.content
let lastSavedTitle = props.note.title

watch(() => props.note.id, async (newId, oldId) => {
  // 切笔记前先保存旧的
  if (oldId !== undefined && oldId !== newId && saveStatus.value === 'dirty') {
    await save()
  }
  title.value = props.note.title
  content.value = props.note.content
  lastSavedContent = props.note.content
  lastSavedTitle = props.note.title
  saveStatus.value = 'saved'
  newTagShowInput.value = false
  newTagInput.value = ''
  await notes.fetchNoteTags(props.note.id)
})

onMounted(async () => {
  await notes.fetchNoteTags(props.note.id)
})

watch([title, content], () => {
  if (title.value === lastSavedTitle && content.value === lastSavedContent) {
    saveStatus.value = 'saved'
    return
  }
  // 标记为"未保存"，但**不自动保存**——用户必须主动点保存按钮 / Ctrl+S / 切笔记
  saveStatus.value = 'dirty'
})

async function save(immediate = false) {
  if (title.value === lastSavedTitle && content.value === lastSavedContent) {
    if (immediate) message.success('已是最新')
    return
  }
  // 立即保存：清掉防抖 timer
  if (saveTimer) {
    clearTimeout(saveTimer)
    saveTimer = null
  }
  saveStatus.value = 'saving'
  try {
    const updated = await notes.updateNote(props.note.id, { title: title.value, content: content.value })
    lastSavedTitle = updated.title
    lastSavedContent = updated.content
    if (title.value !== updated.title) title.value = updated.title
    if (content.value !== updated.content) content.value = updated.content
    saveStatus.value = 'saved'
    if (immediate) message.success('已保存')
  } catch (e: any) {
    saveStatus.value = 'dirty'
    message.error('保存失败：' + (e.response?.data?.detail || e.message))
  }
}

// Ctrl+S 触发保存
function handleKeydown(e: KeyboardEvent) {
  if ((e.ctrlKey || e.metaKey) && e.key === 's') {
    e.preventDefault()
    save(true)
  }
}

// 离开页面前提示
function handleBeforeUnload(e: BeforeUnloadEvent) {
  if (saveStatus.value === 'dirty') {
    e.preventDefault()
    // 现代浏览器会忽略自定义 returnValue，统一显示原生提示即可
    e.returnValue = ''
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  window.addEventListener('beforeunload', handleBeforeUnload)
})

onUnmounted(async () => {
  if (saveTimer) clearTimeout(saveTimer)
  document.removeEventListener('keydown', handleKeydown)
  window.removeEventListener('beforeunload', handleBeforeUnload)
  // 最后一次保存：异步触发，组件卸载期间 store 调用仍能完成
  if (saveStatus.value === 'dirty') {
    try {
      await save()
    } catch {
      // 卸载时静默失败
    }
  }
})

function handleDelete() {
  dialog.warning({
    title: '删除笔记',
    content: `确定删除「${title.value}」？可在「已删除」列表恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      try {
        await notes.deleteNote(props.note.id)
        message.success('已删除，可在「已删除」列表恢复')
      } catch (e: any) {
        message.error('删除失败')
      }
    },
  })
}

function handleExport() {
  const md = noteToMarkdown({
    title: title.value,
    content: content.value,
    tags: notes.currentNoteTags,
    created_at: props.note.created_at,
    updated_at: props.note.updated_at,
  })
  const filename = safeFilename(title.value || '未命名笔记') + '.md'
  downloadFile(filename, md)
  message.success('已导出：' + filename)
}

const renderedContent = computed(() => {
  if (!previewMode.value) return ''
  return DOMPurify.sanitize(marked.parse(content.value || '', { async: false }) as string)
})

// 字数 / 阅读时长
const charCount = computed(() => content.value.length)
// 中文按字数算更直观：去掉空白后的字符数
const wordCount = computed(() => content.value.replace(/\s/g, '').length)
const readMinutes = computed(() => Math.max(1, Math.ceil(wordCount.value / 300)))
// 标题提示
const titleAutoRenamed = computed(() =>
  props.note.title === '未命名笔记' && lastSavedTitle === '未命名笔记' && !title.value.trim()
)

function askAI() {
  chat.ask(`帮我总结这篇笔记「${title.value || '未命名笔记'}」的内容，并提炼 3 个关键点。`)
}

async function addTag() {
  const name = newTagInput.value.trim()
  if (!name) {
    newTagShowInput.value = false
    return
  }
  if (notes.currentNoteTags.includes(name)) {
    message.warning('标签已存在')
    newTagInput.value = ''
    return
  }
  const newTags = [...notes.currentNoteTags, name]
  try {
    await notes.setNoteTags(props.note.id, newTags)
    newTagInput.value = ''
  } catch (e: any) {
    message.error('添加标签失败：' + (e.response?.data?.detail || e.message))
  }
}

async function removeTag(name: string) {
  const newTags = notes.currentNoteTags.filter(t => t !== name)
  try {
    await notes.setNoteTags(props.note.id, newTags)
  } catch (e: any) {
    message.error('删除标签失败')
  }
}
</script>

<template>
  <div class="editor">
    <div class="editor-header">
      <span class="timestamp">{{ new Date(note.created_at).toLocaleString('zh-CN') }}</span>
      <NButton text size="small" @click="askAI" class="ask-ai-btn">✨ 让 AI 总结</NButton>
      <NButton text size="small" @click="previewMode = !previewMode">
        {{ previewMode ? '编辑' : '预览' }}
      </NButton>
      <NButton text size="small" @click="handleExport">导出</NButton>
      <NButton text size="small" @click="handleDelete" type="error">删除</NButton>
    </div>

    <!-- 标签栏 -->
    <div class="tags-bar">
      <NSpace size="small">
        <NTag
          v-for="t in notes.currentNoteTags"
          :key="t"
          size="small"
          closable
          @close="removeTag(t)"
          type="info"
        >
          {{ t }}
        </NTag>
        <NTag
          v-if="!newTagShowInput"
          size="small"
          :bordered="false"
          @click="newTagShowInput = true"
          style="cursor: pointer; opacity: 0.6;"
        >
          ＋ 标签
        </NTag>
        <NInput
          v-else
          v-model:value="newTagInput"
          size="small"
          placeholder="输入标签名..."
          style="width: 140px;"
          autofocus
          @keydown.enter="addTag"
          @blur="newTagShowInput = false; newTagInput = ''"
        />
      </NSpace>
    </div>

    <div class="editor-body">
      <div class="editor-content">
        <input
          v-model="title"
          class="title-input"
          :class="{ 'auto-renamed': titleAutoRenamed }"
          placeholder="标题（留空会自动设为「未命名笔记」）"
        />

        <textarea
          v-if="!previewMode"
          v-model="content"
          class="content-textarea"
          placeholder="开始记录..."
        />

        <div v-else class="content-preview" v-html="renderedContent" />
      </div>
    </div>

    <div class="editor-footer">
      <div class="footer-left">
        <NButton
          size="small"
          :type="saveStatus === 'dirty' ? 'primary' : 'default'"
          :loading="saveStatus === 'saving'"
          :disabled="saveStatus === 'saved' || saveStatus === 'saving'"
          @click="save(true)"
        >
          {{ saveStatus === 'saving' ? '保存中…' : saveStatus === 'saved' ? '已保存' : '保存' }}
        </NButton>
        <span class="save-hint">Ctrl+S</span>
        <span class="separator">·</span>
        <span class="meta">{{ wordCount }} 字 · 约 {{ readMinutes }} 分钟阅读</span>
      </div>
      <NButton class="ai-launcher" @click="askAI" size="small">
        ✨ AI 对话
      </NButton>
    </div>
  </div>
</template>

<style scoped>
.editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  max-width: 800px;
  margin: 0 auto;
}
.editor-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 40px 8px;
  color: var(--text-3, #9a9aa0);
  font-size: 12px;
}
.ask-ai-btn {
  color: #8b5cf6 !important;
  font-weight: 500;
}
.tags-bar {
  padding: 0 40px 8px;
  border-bottom: 1px solid var(--border-soft, #e8e8ec);
  margin-bottom: 8px;
  min-height: 32px;
  display: flex;
  align-items: center;
}
.editor-body {
  flex: 1;
  overflow-y: auto;
  padding: 0 40px 40px;
}
.editor-content {
  font-size: 15px;
  line-height: 1.75;
  color: var(--text, #1d1d1f);
}
.title-input {
  width: 100%;
  font-size: 28px;
  font-weight: 600;
  border: none;
  outline: none;
  padding: 8px 0;
  margin-bottom: 16px;
  background: transparent;
  color: inherit;
}
.title-input.auto-renamed {
  color: var(--text-3, #9a9aa0);
  font-style: italic;
}
.content-textarea {
  width: 100%;
  min-height: 60vh;
  border: none;
  outline: none;
  resize: none;
  font: inherit;
  background: transparent;
  color: inherit;
}
.content-preview {
  padding: 12px 0;
}
.content-preview :deep(h1) { font-size: 1.6em; margin: 0.8em 0 0.4em; }
.content-preview :deep(h2) { font-size: 1.3em; margin: 0.6em 0 0.3em; }
.content-preview :deep(p) { margin: 0.4em 0; }
.content-preview :deep(ul), .content-preview :deep(ol) { padding-left: 1.5em; }
.content-preview :deep(code) {
  background: var(--bg-hover, #e3e3e6);
  padding: 2px 6px;
  border-radius: 4px;
  font-family: ui-monospace, monospace;
  font-size: 0.9em;
}
.content-preview :deep(pre) {
  background: var(--bg-hover, #e3e3e6);
  padding: 12px;
  border-radius: 8px;
  overflow-x: auto;
}
.content-preview :deep(blockquote) {
  border-left: 3px solid #8b5cf6;
  padding-left: 12px;
  color: var(--text-2, #6e6e73);
  margin: 0.6em 0;
}
.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 40px;
  border-top: 1px solid var(--border-soft, #e8e8ec);
}
.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-3, #9a9aa0);
}
.save-hint {
  font-family: ui-monospace, monospace;
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-hover, #e3e3e6);
  border-radius: 4px;
  color: var(--text-2, #6e6e73);
}
.separator { opacity: 0.5; }
.meta { color: var(--text-2, #6e6e73); }
.ai-launcher {
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #ec4899 100%) !important;
  color: white !important;
  font-weight: 500 !important;
  border: none !important;
}
</style>
