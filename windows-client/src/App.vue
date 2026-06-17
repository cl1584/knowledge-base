<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { NConfigProvider, NMessageProvider, NDialogProvider, darkTheme } from 'naive-ui'
import { useSettingsStore } from '@/stores/settings'
import { useNotesStore } from '@/stores/notes'
import { RouterView, useRoute } from 'vue-router'
import ShortcutsModal from '@/components/ShortcutsModal.vue'
import ErrorBoundary from '@/components/ErrorBoundary.vue'

const settings = useSettingsStore()
const notes = useNotesStore()
const route = useRoute()
// Note: useMessage() can only be used inside NMessageProvider tree.
// App.vue IS the provider, so we use console.error for global shortcut errors.

const showShortcuts = ref(false)

onMounted(() => {
  settings.init()
  // auth state 已从 store 初始化时从 localStorage 自动恢复，无需 restoreSession
  document.addEventListener('keydown', handleGlobalKey)
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleGlobalKey)
})

function handleGlobalKey(e: KeyboardEvent) {
  const target = e.target as HTMLElement
  const inEditor = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable

  // ? 打开帮助（在非输入框里）
  if (e.key === '?' && !e.ctrlKey && !e.metaKey && !inEditor) {
    e.preventDefault()
    showShortcuts.value = !showShortcuts.value
    return
  }

  // 登录页不响应
  if (route.name === 'login') return

  // Ctrl+N 新建
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'n' && !e.shiftKey) {
    e.preventDefault()
    if (notes) {
      notes.createNote().catch((err: any) => {
        console.error('创建失败：', err.response?.data?.detail || err.message)
      })
    }
    return
  }

  // Ctrl+K 搜索（在 HomeView 里通过 emit 触发更合理，先弹个 toast 提示去点搜索框）
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k' && !e.shiftKey) {
    e.preventDefault()
    // 触发搜索：派发一个自定义事件
    window.dispatchEvent(new CustomEvent('kb:open-search'))
    return
  }
}
</script>

<template>
  <NConfigProvider :theme="settings.isDark ? darkTheme : null">
    <NMessageProvider>
      <NDialogProvider>
        <ErrorBoundary>
          <RouterView />
        </ErrorBoundary>
        <ShortcutsModal v-model:show="showShortcuts" />
      </NDialogProvider>
    </NMessageProvider>
  </NConfigProvider>
</template>

<style>
#app {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
</style>
