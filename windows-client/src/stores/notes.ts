/** Notes Store：当前笔记列表 + 选中 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { notesApi, type Note } from '@/api/notes'
import { tagsApi, type Tag } from '@/api/tags'

export const useNotesStore = defineStore('notes', () => {
  const notes = ref<Note[]>([])
  const deletedNotes = ref<Note[]>([])
  const currentId = ref<number | null>(null)
  const loading = ref(false)
  const hasMore = ref(true)
  const total = ref(0)
  const searchKeyword = ref('')
  const allTags = ref<Tag[]>([])
  const currentNoteTags = ref<string[]>([])  // 当前笔记的标签名
  const activeTagIds = ref<number[]>([])     // 当前筛选的标签

  const current = computed<Note | null>(() =>
    notes.value.find(n => n.id === currentId.value) || null
  )

  const groupedNotes = computed(() => {
    const groups: Record<string, Note[]> = {}
    for (const n of notes.value) {
      const key = groupKey(n.created_at)
      if (!groups[key]) groups[key] = []
      groups[key].push(n)
    }
    return groups
  })

  const PAGE_SIZE = 30
  let offset = 0

  async function fetchList(keyword = '', reset = true) {
    if (loading.value) return
    if (reset) {
      offset = 0
      hasMore.value = true
    }
    if (!hasMore.value) return
    loading.value = true
    try {
      const params: any = {
        keyword: keyword || undefined,
        is_archived: false,
        limit: PAGE_SIZE,
        offset,
      }
      if (activeTagIds.value.length > 0) {
        params.tag_id = activeTagIds.value
      }
      const resp = await notesApi.list(params)
      if (reset) {
        notes.value = resp.items
      } else {
        // 追加模式：去重后追加
        const existIds = new Set(notes.value.map(n => n.id))
        for (const item of resp.items) {
          if (!existIds.has(item.id)) notes.value.push(item)
        }
      }
      hasMore.value = resp.has_more
      total.value = resp.total
      offset += resp.items.length
      if (!currentId.value && notes.value.length > 0) {
        currentId.value = notes.value[0].id
      }
    } finally {
      loading.value = false
    }
  }

  async function loadMore() {
    if (!hasMore.value || loading.value) return
    await fetchList(searchKeyword.value, false)
  }

  function toggleTagFilter(tagId: number) {
    const idx = activeTagIds.value.indexOf(tagId)
    if (idx >= 0) {
      activeTagIds.value.splice(idx, 1)
    } else {
      activeTagIds.value.push(tagId)
    }
    fetchList(searchKeyword.value, true)
  }

  function clearTagFilter() {
    activeTagIds.value = []
    fetchList(searchKeyword.value, true)
  }

  async function fetchDeleted() {
    loading.value = true
    try {
      // 后端 include_deleted=true 时只返回已删除的，不再叠加 is_archived
      const resp = await notesApi.list({ include_deleted: true })
      deletedNotes.value = resp.items
    } finally {
      loading.value = false
    }
  }

  async function fetchAllTags() {
    try {
      allTags.value = await tagsApi.list()
    } catch (e) {
      console.error('Failed to fetch tags', e)
    }
  }

  async function fetchNoteTags(noteId: number) {
    try {
      const tags = await tagsApi.getNoteTags(noteId)
      currentNoteTags.value = tags.map(t => t.name)
    } catch (e) {
      currentNoteTags.value = []
    }
  }

  async function setNoteTags(noteId: number, names: string[]) {
    await tagsApi.setNoteTags(noteId, names)
    currentNoteTags.value = names
    await fetchAllTags()  // 刷新标签列表
  }

  async function search(keyword: string) {
    searchKeyword.value = keyword
    await fetchList(keyword, true)
  }

  async function createNote() {
    const note = await notesApi.create('', '')
    notes.value.unshift(note)
    currentId.value = note.id
    return note
  }

  async function updateNote(id: number, data: { title?: string; content?: string }) {
    const updated = await notesApi.update(id, data)
    const idx = notes.value.findIndex(n => n.id === id)
    if (idx >= 0) notes.value[idx] = updated
    return updated
  }

  async function deleteNote(id: number, permanent = false) {
    const idx = notes.value.findIndex(n => n.id === id)
    if (idx === -1) return
    const backup = notes.value[idx]
    // 乐观更新：先本地移除
    notes.value.splice(idx, 1)
    if (currentId.value === id) {
      currentId.value = notes.value[0]?.id || null
    }
    try {
      await notesApi.remove(id, permanent)
    } catch {
      // 失败回滚
      notes.value.splice(idx, 0, backup)
      if (currentId.value === null && backup) currentId.value = backup.id
    }
  }

  async function restoreNote(id: number) {
    const idx = deletedNotes.value.findIndex(n => n.id === id)
    if (idx === -1) return
    const backup = deletedNotes.value[idx]
    deletedNotes.value.splice(idx, 1)
    try {
      const restored = await notesApi.restore(id)
      notes.value.unshift(restored)
      currentId.value = restored.id
    } catch {
      deletedNotes.value.splice(idx, 0, backup)
    }
    return
  }

  function selectNote(id: number) {
    currentId.value = id
  }

  function groupKey(isoDate: string): string {
    const d = new Date(isoDate)
    const now = new Date()
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterday = new Date(today)
    yesterday.setDate(today.getDate() - 1)
    const noteDay = new Date(d.getFullYear(), d.getMonth(), d.getDate())
    if (noteDay.getTime() === today.getTime()) return '今天'
    if (noteDay.getTime() === yesterday.getTime()) return '昨天'
    if (noteDay.getFullYear() === now.getFullYear()) {
      return `${d.getMonth() + 1}月${d.getDate()}日`
    }
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
  }

  return {
    notes, deletedNotes, currentId, current, loading, hasMore, total, searchKeyword, groupedNotes,
    allTags, currentNoteTags, activeTagIds,
    fetchList, loadMore, fetchDeleted, fetchAllTags, fetchNoteTags, setNoteTags,
    search, createNote, updateNote, deleteNote, restoreNote, selectNote,
    toggleTagFilter, clearTagFilter,
  }
})
