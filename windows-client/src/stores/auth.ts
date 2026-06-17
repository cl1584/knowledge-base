/** Auth Store：登录状态 + token */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi, type User } from '@/api/auth'

const TOKEN_KEY = 'kb-token'
const USER_KEY = 'kb-user'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(JSON.parse(localStorage.getItem(USER_KEY) || 'null'))
  // 用于 401 时区分：true=已登录被踢，false=登录页失败（不要弹"已登出"）
  const wasLoggedIn = ref(!!localStorage.getItem(TOKEN_KEY))

  const isLoggedIn = computed(() => !!token.value)

  async function login(username: string, password: string) {
    const resp = await authApi.login(username, password)
    token.value = resp.access_token
    user.value = resp.user
    wasLoggedIn.value = true
    localStorage.setItem(TOKEN_KEY, resp.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user))
  }

  async function register(username: string, password: string, nickname?: string) {
    const resp = await authApi.register(username, password, nickname)
    token.value = resp.access_token
    user.value = resp.user
    wasLoggedIn.value = true
    localStorage.setItem(TOKEN_KEY, resp.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(resp.user))
  }

  async function fetchUser() {
    try {
      const u = await authApi.me()
      user.value = u
      localStorage.setItem(USER_KEY, JSON.stringify(u))
    } catch (e: any) {
      // token 过期则登出
      if (e?.response?.status === 401) logout()
    }
  }

  function logout() {
    token.value = null
    user.value = null
    wasLoggedIn.value = false
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return { token, user, isLoggedIn, wasLoggedIn, login, register, fetchUser, logout }
})
