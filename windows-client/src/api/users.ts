import api from './index'

export interface AISettingsResponse {
  has_key: boolean
  base_url: string
  model: string
}

export interface AISettingsUpdate {
  api_key?: string | null   // null=不修改；""=清除；其他=写入
  base_url?: string
  model?: string
}

export async function getAISettings(): Promise<AISettingsResponse> {
  const { data } = await api.get('/users/me/ai-settings')
  return data
}

export async function updateAISettings(req: AISettingsUpdate): Promise<{ ok: boolean; has_key: boolean }> {
  const { data } = await api.post('/users/me/ai-settings', req)
  return data
}
