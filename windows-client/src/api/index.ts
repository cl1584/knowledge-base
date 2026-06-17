/**
 * API 客户端：调用后端 FastAPI
 * baseURL 在请求时从 localStorage 读，改设置立即生效
 */
import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
} from 'axios'
import { useAuthStore } from '@/stores/auth'

// 扩展 axios config 类型，加自定义重试字段
declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    __retryCount?: number
  }
}

const DEFAULT_BASE = import.meta.env.VITE_API_BASE || 'http://127.0.0.1:8765'

function getApiBase(): string {
  try {
    const s = localStorage.getItem('kb-settings')
    if (s) {
      const parsed = JSON.parse(s)
      if (parsed.apiBase) return parsed.apiBase
    }
  } catch {}
  return DEFAULT_BASE
}

const api: AxiosInstance = axios.create({
  baseURL: DEFAULT_BASE,
  timeout: 30000,
})

// === 重试：网络错误 / 5xx 最多重试 2 次，指数退避 ===
function shouldRetry(config: InternalAxiosRequestConfig, err: any): boolean {
  if (!config) return false
  const retries = config.__retryCount || 0
  if (retries >= 2) return false
  if (axios.isCancel(err)) return false
  // 网络错误 / 5xx 重试
  if (!err.response) return true
  if (err.response.status >= 500) return true
  return false
}

// 请求拦截：动态 baseURL + 附加 token
api.interceptors.request.use((config) => {
  config.baseURL = getApiBase()
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截：401 自动登出 + 网络/5xx 自动重试
api.interceptors.response.use(
  (r) => r,
  async (err) => {
    const config = err?.config as InternalAxiosRequestConfig | undefined
    if (err.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      // 仅在有 token 时提示，避免登录页本身无限重定向
      if (auth.wasLoggedIn) {
        console.warn('[API] 401 已自动登出')
      }
      return Promise.reject(err)
    }
    if (config && shouldRetry(config, err)) {
      config.__retryCount = (config.__retryCount || 0) + 1
      const delay = 300 * Math.pow(2, config.__retryCount - 1)
      await new Promise((r) => setTimeout(r, delay))
      return api.request(config)
    }
    // 4xx 非 401 走默认 reject（业务层 catch 处理）
    return Promise.reject(err)
  }
)

export default api
export { getApiBase }


