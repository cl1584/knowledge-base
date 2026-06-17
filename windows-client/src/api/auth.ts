/** Auth API */
import api from './index'

export interface User {
  id: number
  username: string
  nickname: string
  avatar: string
  has_ai_key: boolean
  ai_base_url: string
  ai_model: string
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export const authApi = {
  login: (username: string, password: string) =>
    api.post<TokenResponse>('/api/auth/login', { username, password }).then(r => r.data),

  register: (username: string, password: string, nickname?: string) =>
    api.post<TokenResponse>('/api/auth/register', { username, password, nickname }).then(r => r.data),

  me: () => api.get<User>('/api/auth/me').then(r => r.data),
}
