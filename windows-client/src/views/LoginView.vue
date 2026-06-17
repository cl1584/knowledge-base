<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NCard, NInput, NButton, NSpace, NAlert, NForm, NFormItem, NSpin } from 'naive-ui'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import api from '@/api'

const auth = useAuthStore()
const settings = useSettingsStore()
const router = useRouter()
const route = useRoute()

const username = ref('')
const password = ref('')
const isRegister = ref(false)
const loading = ref(false)
const error = ref('')

// API 地址（独立 ref，编辑时不影响 store，点了"应用"才生效）
const apiBaseInput = ref(settings.apiBase)
const testing = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)

const apiBaseDirty = computed(() => apiBaseInput.value.trim() !== settings.apiBase)

onMounted(() => {
  // 从 localStorage 直接同步一次（不依赖 settings.init() 时机）
  try {
    const raw = localStorage.getItem('kb-settings')
    if (raw) {
      const s = JSON.parse(raw)
      if (s.apiBase) apiBaseInput.value = s.apiBase
    }
  } catch {}
})

async function testConnection() {
  const url = apiBaseInput.value.trim().replace(/\/+$/, '')
  if (!url) {
    testResult.value = { ok: false, msg: '请输入后端地址' }
    return
  }
  testing.value = true
  testResult.value = null
  try {
    const resp = await api.get('/api/health', {
      baseURL: url,
      timeout: 5000,
    })
    if (resp.data?.status === 'ok') {
      testResult.value = {
        ok: true,
        msg: `✓ ${resp.data.app || '后端'} (v${resp.data.version || '?'})`,
      }
    } else {
      testResult.value = { ok: false, msg: '后端返回了非预期响应' }
    }
  } catch (e: any) {
    let msg = '连接失败'
    if (e.code === 'ERR_NETWORK' || e.message?.includes('Network Error')) {
      msg = `无法连接 ${url}（确认后端已启动、防火墙已放行）`
    } else if (e.code === 'ECONNABORTED') {
      msg = '连接超时（5s）'
    } else if (e.response?.status) {
      msg = `HTTP ${e.response.status}`
    }
    testResult.value = { ok: false, msg }
  } finally {
    testing.value = false
  }
}

function applyApiBase() {
  const url = apiBaseInput.value.trim().replace(/\/+$/, '')
  if (!url) return
  settings.setApiBase(url)
  testResult.value = { ok: true, msg: '已应用（点击登录使用新地址）' }
}

function useDefaultLocal() {
  apiBaseInput.value = 'http://127.0.0.1:8000'
}

async function submit() {
  if (loading.value) return
  if (!username.value || !password.value) {
    error.value = '请填写用户名和密码'
    return
  }
  if (isRegister.value) {
    if (username.value.length < 3) {
      error.value = '用户名至少 3 个字符'
      return
    }
    if (password.value.length < 6) {
      error.value = '密码至少 6 个字符'
      return
    }
  }
  loading.value = true
  error.value = ''
  try {
    if (isRegister.value) {
      await auth.register(username.value, password.value, username.value)
    } else {
      await auth.login(username.value, password.value)
    }
    const redirect = (route.query.redirect as string) || '/'
    await router.push(redirect)
  } catch (e: any) {
    console.error('Auth error:', e)
    if (e.code === 'ERR_NETWORK' || e.message?.includes('Network Error')) {
      error.value = `无法连接服务器：${settings.apiBase}\n请确认后端已启动`
    } else if (typeof e.response?.data?.detail === 'string') {
      error.value = e.response.data.detail
    } else if (Array.isArray(e.response?.data?.detail)) {
      const msgs = e.response.data.detail.map((d: any) => {
        const field = d.loc?.slice(-1)[0] || '字段'
        return `${field}: ${d.msg}`
      })
      error.value = msgs.join('；')
    } else {
      error.value = e.message || '操作失败'
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <NCard class="login-card" :bordered="false">
      <div class="logo">📝</div>
      <h1>知识库</h1>
      <p class="subtitle">Personal AI Knowledge Base</p>

      <!-- 后端地址 -->
      <div class="api-section">
        <div class="api-label">
          <span>后端地址</span>
          <button type="button" class="api-reset" @click="useDefaultLocal">重置</button>
        </div>
        <div class="api-row">
          <NInput
            v-model:value="apiBaseInput"
            placeholder="http://192.168.1.100:8000"
            size="medium"
            :status="testResult?.ok === false ? 'error' : testResult?.ok === true ? 'success' : undefined"
            @keydown.enter.prevent="testConnection"
          />
          <NButton
            size="medium"
            :loading="testing"
            @click="testConnection"
          >
            测试
          </NButton>
        </div>
        <div v-if="testResult" class="api-result" :class="{ ok: testResult.ok, err: !testResult.ok }">
          {{ testResult.msg }}
        </div>
        <NButton
          v-if="apiBaseDirty"
          size="tiny"
          type="primary"
          block
          style="margin-top: 6px"
          @click="applyApiBase"
        >
          应用新地址
        </NButton>
      </div>

      <NForm @submit.prevent="submit">
        <NFormItem>
          <NInput
            v-model:value="username"
            placeholder="用户名"
            size="large"
            autofocus
          />
        </NFormItem>
        <NFormItem>
          <NInput
            v-model:value="password"
            type="password"
            show-password-on="click"
            placeholder="密码"
            size="large"
          />
        </NFormItem>

        <NAlert v-if="error" type="error" :show-icon="false" style="margin-bottom: 16px; white-space: pre-line">
          {{ error }}
        </NAlert>

        <NSpace vertical size="medium">
          <NButton
            type="primary"
            size="large"
            block
            :loading="loading"
            native-type="submit"
          >
            {{ isRegister ? '注册' : '登录' }}
          </NButton>
          <NButton text size="small" @click="isRegister = !isRegister">
            {{ isRegister ? '已有账号？登录' : '没有账号？注册' }}
          </NButton>
        </NSpace>

        <p v-if="isRegister" class="form-hint">
          用户名至少 3 个字符，密码至少 6 个字符
        </p>
      </NForm>
    </NCard>
  </div>
</template>

<style scoped>
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%);
}
.login-card {
  width: 400px;
  padding: 28px 32px 32px;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.08);
}
.logo {
  text-align: center;
  font-size: 48px;
  margin-bottom: 4px;
}
h1 {
  text-align: center;
  font-size: 22px;
  font-weight: 600;
  margin: 0 0 4px;
}
.subtitle {
  text-align: center;
  color: var(--text-2, #6e6e73);
  font-size: 12px;
  margin: 0 0 20px;
}
.api-section {
  margin-bottom: 18px;
  padding: 12px;
  background: var(--bg-soft, #f5f5f7);
  border-radius: 8px;
  border: 1px solid var(--border-soft, #e8e8ec);
}
.api-label {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-2, #6e6e73);
  margin-bottom: 8px;
}
.api-reset {
  background: none;
  border: none;
  color: var(--text-3, #9a9aa0);
  cursor: pointer;
  font-size: 11px;
  padding: 0;
}
.api-reset:hover { color: var(--accent, #6366f1); }
.api-row {
  display: flex;
  gap: 8px;
}
.api-row :deep(.n-input) { flex: 1; }
.api-result {
  margin-top: 6px;
  font-size: 12px;
  font-family: ui-monospace, monospace;
}
.api-result.ok { color: #18a058; }
.api-result.err { color: #d03050; }
.form-hint {
  text-align: center;
  color: var(--text-3, #9a9aa0);
  font-size: 11px;
  margin: 8px 0 0;
}
</style>
