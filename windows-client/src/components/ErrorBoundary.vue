<script setup lang="ts">
/**
 * Vue 错误边界：捕获子组件错误，显示降级 UI，不让整个 App 崩溃
 */
import { onErrorCaptured, ref } from 'vue'

const props = defineProps<{ fallbackTitle?: string }>()

const error = ref<Error | null>(null)
const errorInfo = ref<string>('')
const errorStack = ref<string>('')

onErrorCaptured((err: any, instance: any, info) => {
  console.error('[ErrorBoundary] caught:', err, info, 'instance:', instance)
  error.value = err
  errorInfo.value = info || ''
  // 拼一份诊断信息：哪个组件的 setup 在哪个 instance 上
  // (instance 内部组件；用 (instance as any) 绕过 TS 类型）
  const inst: any = instance
  const compName = inst?.$options?.name || inst?.type?.__name || 'unknown'
  const compFile = inst?.type?.__file || ''
  errorInfo.value = info ? `${info} @ <${compName}> ${compFile}` : `<${compName}> ${compFile}`
  errorStack.value = err?.stack || ''
  return false
})

function reset() {
  error.value = null
  errorInfo.value = ''
  errorStack.value = ''
}

function reload() {
  location.reload()
}

function copyError() {
  const text = `[ErrorBoundary] ${error.value?.message}\n\n${errorStack.value}\n\nInfo: ${errorInfo.value}`
  navigator.clipboard?.writeText(text).then(() => {
    alert('错误信息已复制到剪贴板')
  }).catch(() => {
    alert('复制失败，请手动截图')
  })
}
</script>

<template>
  <div v-if="error" class="error-fallback">
    <div class="error-icon">⚠️</div>
    <h2>{{ props.fallbackTitle || '应用出错了' }}</h2>
    <p class="error-msg">{{ error.message || '未知错误' }}</p>
    <p v-if="errorInfo" class="error-info">位置：{{ errorInfo }}</p>
    <details v-if="errorStack" class="error-stack-wrap">
      <summary>查看堆栈（点击展开）</summary>
      <pre class="error-stack">{{ errorStack }}</pre>
    </details>
    <div class="error-actions">
      <button @click="reset">重试</button>
      <button @click="copyError">复制错误</button>
      <button @click="reload" class="primary">刷新页面</button>
    </div>
    <p class="error-hint">💡 提示：把错误信息发给 AI 助手能更快定位问题</p>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-fallback {
  position: fixed;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 24px;
  background: var(--bg-page, #0e0e10);
  color: var(--text, #e8e8ea);
  z-index: 9999;
  overflow: auto;
}
.error-icon { font-size: 64px; margin-bottom: 16px; }
h2 { margin: 0 0 16px; font-size: 22px; font-weight: 600; }
.error-msg {
  color: #ff6b6b;
  font-family: ui-monospace, 'Cascadia Code', 'Consolas', monospace;
  font-size: 14px;
  background: rgba(255, 107, 107, 0.12);
  padding: 12px 16px;
  border-radius: 8px;
  margin: 0 0 12px;
  word-break: break-all;
  max-width: 720px;
  text-align: center;
  border: 1px solid rgba(255, 107, 107, 0.3);
}
.error-info {
  font-size: 13px;
  color: #9a9aa0;
  margin: 0 0 16px;
}
.error-stack-wrap {
  max-width: 720px;
  width: 100%;
  margin-bottom: 20px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 12px 16px;
}
.error-stack-wrap summary {
  cursor: pointer;
  font-size: 13px;
  color: #9a9aa0;
  user-select: none;
}
.error-stack {
  margin: 12px 0 0;
  padding: 12px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
  font-size: 12px;
  line-height: 1.5;
  overflow: auto;
  max-height: 320px;
  white-space: pre-wrap;
  word-break: break-all;
  color: #d8d8da;
}
.error-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.error-actions button {
  padding: 10px 24px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.06);
  color: inherit;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.12s;
}
.error-actions button:hover { background: rgba(255, 255, 255, 0.12); }
.error-actions button.primary {
  background: #6366f1;
  color: white;
  border-color: #6366f1;
}
.error-actions button.primary:hover { background: #5558e0; }
.error-hint {
  font-size: 12px;
  color: #6a6a70;
  margin: 0;
}
</style>
