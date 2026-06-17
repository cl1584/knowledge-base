<script setup lang="ts">
import { NDrawer, NDrawerContent, NRadioGroup, NRadio, NInput, NButton, NSpace, NDivider, NSelect, useMessage } from 'naive-ui'
import { useSettingsStore } from '@/stores/settings'
import { useAuthStore } from '@/stores/auth'
import { useChatStore } from '@/stores/chat'
import { getAISettings, updateAISettings } from '@/api/users'
import { ref, watch } from 'vue'

const props = defineProps<{ show: boolean }>()
const emit = defineEmits<{ (e: 'update:show', v: boolean): void }>()

const settings = useSettingsStore()
const auth = useAuthStore()
const chat = useChatStore()
const message = useMessage()

const apiBase = ref(settings.apiBase)

// ── 模型预设 ──
interface ModelPreset {
  label: string
  base_url: string
  model: string
  placeholder_key: string
}

const PRESETS: Record<string, ModelPreset> = {
  deepseek: {
    label: 'DeepSeek',
    base_url: 'https://api.deepseek.com',
    model: 'deepseek-chat',
    placeholder_key: 'sk-...',
  },
  openai: {
    label: 'OpenAI',
    base_url: 'https://api.openai.com/v1',
    model: 'gpt-4o',
    placeholder_key: 'sk-...',
  },
  qwen: {
    label: '通义千问（阿里云）',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    model: 'qwen-plus',
    placeholder_key: 'sk-...',
  },
  claude_openrouter: {
    label: 'Claude（OpenRouter）',
    base_url: 'https://openrouter.ai/api/v1',
    model: 'anthropic/claude-3.5-sonnet',
    placeholder_key: 'sk-or-...',
  },
  ollama: {
    label: 'Ollama（本地）',
    base_url: 'http://localhost:11434/v1',
    model: 'llama3',
    placeholder_key: '（本地不需要 key，填空或任意值）',
  },
  custom: {
    label: '自定义',
    base_url: '',
    model: '',
    placeholder_key: '',
  },
}

const presetOptions = [
  { label: 'DeepSeek', value: 'deepseek' },
  { label: 'OpenAI', value: 'openai' },
  { label: '通义千问（阿里云）', value: 'qwen' },
  { label: 'Claude（OpenRouter）', value: 'claude_openrouter' },
  { label: 'Ollama（本地）', value: 'ollama' },
  { label: '✏️ 自定义', value: 'custom' },
]

const selectedPreset = ref<string | null>(null)

function applyPreset(val: string) {
  const p = PRESETS[val]
  if (!p) return
  aiBaseUrl.value = p.base_url
  aiModel.value = p.model
  selectedPreset.value = val
}

function onPresetChange(val: string | null) {
  if (!val) {
    selectedPreset.value = null
    return
  }
  applyPreset(val)
}

// AI 设置表单
const aiKey = ref('')
const aiBaseUrl = ref('')
const aiModel = ref('')
const showKey = ref(false)
const aiLoading = ref(false)
const aiKeySaved = ref(false)

// 监听 base_url / model 手动编辑，若和当前预设不一致则切到自定义
watch([aiBaseUrl, aiModel], () => {
  if (!selectedPreset.value || selectedPreset.value === 'custom') return
  const p = PRESETS[selectedPreset.value]
  if (!p) return
  if (aiBaseUrl.value !== p.base_url || aiModel.value !== p.model) {
    selectedPreset.value = 'custom'
  }
})

watch(() => props.show, async (v) => {
  if (v) {
    apiBase.value = settings.apiBase
    try {
      const data = await getAISettings()
      aiBaseUrl.value = data.base_url || ''
      aiModel.value = data.model || ''
      aiKeySaved.value = data.has_key
      aiKey.value = ''
      // 反向匹配预设
      selectedPreset.value = null
      for (const [k, p] of Object.entries(PRESETS)) {
        if (k === 'custom') continue
        if (p.base_url && p.model && aiBaseUrl.value === p.base_url && aiModel.value === p.model) {
          selectedPreset.value = k
          break
        }
      }
    } catch {}
  }
})

async function saveAiSettings() {
  aiLoading.value = true
  try {
    const req: any = {}
    if (aiKey.value !== '') {
      req.api_key = aiKey.value
    }
    if (aiBaseUrl.value) req.base_url = aiBaseUrl.value
    if (aiModel.value) req.model = aiModel.value
    const res = await updateAISettings(req)
    aiKeySaved.value = res.has_key
    aiKey.value = ''
    message.success('AI 设置已保存')
    await auth.fetchUser()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '保存失败')
  } finally {
    aiLoading.value = false
  }
}

function save() {
  settings.setApiBase(apiBase.value)
  message.success('设置已保存，立即生效')
}

function clearLocalData() {
  localStorage.clear()
  message.success('本地数据已清空，请重启应用')
  setTimeout(() => location.reload(), 800)
}
</script>

<template>
  <NDrawer
    :show="show"
    :width="380"
    placement="right"
    @update:show="emit('update:show', $event)"
  >
    <NDrawerContent title="设置" :native-scrollbar="false">
      <div class="setting-section">
        <div class="setting-label">账户</div>
        <div v-if="auth.user" class="setting-row">
          <div>
            <div class="setting-row-label">{{ auth.user.nickname || auth.user.username }}</div>
            <div class="setting-row-desc">@{{ auth.user.username }}</div>
          </div>
        </div>
      </div>

      <div class="setting-section">
        <div class="setting-label">后端连接</div>
        <div class="setting-row">
          <div class="setting-row-label">API 地址</div>
        </div>
        <NInput
          v-model:value="apiBase"
          placeholder="http://127.0.0.1:8765"
          style="margin-top: 8px"
        />
        <NButton size="small" type="primary" @click="save" style="margin-top: 8px">
          保存
        </NButton>

        <div class="setting-row" style="margin-top: 16px;">
          <div>
            <div class="setting-row-label">AI 状态</div>
            <div class="setting-row-desc">
              <span :style="{ color: aiKeySaved ? '#00b894' : '#e17055' }">●</span>
              {{ aiKeySaved ? '已配置 API Key' : '未配置（演示模式）' }}
            </div>
          </div>
        </div>
      </div>

      <div class="setting-section">
        <div class="setting-label">AI 模型配置</div>

        <div class="setting-row">
          <div class="setting-row-label">模型预设</div>
        </div>
        <NSelect
          v-model:value="selectedPreset"
          :options="presetOptions"
          placeholder="选择一个模型…"
          style="margin-top: 8px"
          @update:value="onPresetChange"
        />
        <div v-if="selectedPreset && selectedPreset !== 'custom'" style="font-size:11px;color:var(--text-3);margin-top:4px;">
          已选择预设，下方配置已自动填写，可手动修改
        </div>
        <div v-else-if="selectedPreset === 'custom'" style="font-size:11px;color:var(--text-3);margin-top:4px;">
          自定义模式，请手动填写 Base URL 和模型名称
        </div>

        <div class="setting-row" style="margin-top:14px;">
          <div class="setting-row-label">API Key</div>
        </div>
        <div style="display:flex;gap:8px;align-items:center;">
          <NInput
            v-model:value="aiKey"
            :type="showKey ? 'text' : 'password'"
            :placeholder="selectedPreset && PRESETS[selectedPreset]?.placeholder_key || 'sk-...（留空则不修改）'"
            style="flex:1"
          />
          <NButton size="tiny" @click="showKey = !showKey">
            {{ showKey ? '隐藏' : '显示' }}
          </NButton>
        </div>
        <div style="font-size:11px;color:var(--text-3);margin-top:4px;">
          {{ aiKeySaved ? '✓ 已保存' : '未配置，聊天将走演示模式' }}
        </div>

        <div class="setting-row" style="margin-top:14px;">
          <div class="setting-row-label">Base URL</div>
        </div>
        <NInput
          v-model:value="aiBaseUrl"
          placeholder="https://api.deepseek.com"
        />
        <div style="font-size:11px;color:var(--text-3);margin-top:4px;">
          OpenAI 兼容接口地址
        </div>

        <div class="setting-row" style="margin-top:14px;">
          <div class="setting-row-label">模型名称</div>
        </div>
        <NInput
          v-model:value="aiModel"
          placeholder="deepseek-chat"
        />
        <div style="font-size:11px;color:var(--text-3);margin-top:4px;">
          对应 Base URL 的模型 ID
        </div>

        <NButton
          size="small"
          type="primary"
          :loading="aiLoading"
          @click="saveAiSettings"
          style="margin-top:14px;width:100%;"
        >
          保存 AI 设置
        </NButton>
      </div>

      <div class="setting-section">
        <div class="setting-label">外观</div>
        <div class="setting-row">
          <div class="setting-row-label">主题</div>
        </div>
        <NRadioGroup :value="settings.theme" @update:value="settings.setTheme" style="margin-top: 8px">
          <NRadio value="light">☀️ 浅色</NRadio>
          <NRadio value="dark">🌙 深色</NRadio>
          <NRadio value="cyber">⚡ 赛博</NRadio>
        </NRadioGroup>
      </div>

      <div class="setting-section">
        <div class="setting-label">数据</div>
        <div class="setting-row">
          <div class="setting-row-label">清空本地数据</div>
        </div>
        <NButton size="small" type="error" @click="clearLocalData" style="margin-top: 8px">
          清空 Token 和本地缓存
        </NButton>
      </div>

      <NDivider />
      <p class="version">知识库 v0.1.0 · Tauri 2.0 + Vue 3</p>
    </NDrawerContent>
  </NDrawer>
</template>

<style scoped>
.setting-section {
  padding: 16px 0;
  border-bottom:1px solid var(--border-soft, #e8e8ec);
}
.setting-section:last-of-type { border-bottom: none; }
.setting-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--text-3, #9a9aa0);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}
.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0;
}
.setting-row-label {
  font-size: 14px;
}
.setting-row-desc {
  font-size: 12px;
  color: var(--text-3, #9a9aa0);
  margin-top: 2px;
}
.version {
  text-align: center;
  color: var(--text-3, #9a9aa0);
  font-size: 11px;
  margin-top: 24px;
}
</style>
