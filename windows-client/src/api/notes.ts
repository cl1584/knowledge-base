/** Notes API */
import api from './index'

export interface Note {
  id: number
  user_id: number
  title: string
  content: string
  is_pinned: boolean
  is_archived: boolean
  created_at: string
  updated_at: string
}

export interface NoteListResponse {
  items: Note[]
  total: number
  has_more: boolean
}

export const notesApi = {
  list: (params: { keyword?: string; is_archived?: boolean; include_deleted?: boolean; tag_id?: number[]; limit?: number; offset?: number } = {}) =>
    api.get<NoteListResponse>('/api/notes', { params }).then(r => r.data),

  get: (id: number) => api.get<Note>(`/api/notes/${id}`).then(r => r.data),

  create: (title: string, content: string) =>
    api.post<Note>('/api/notes', { title, content }).then(r => r.data),

  update: (id: number, data: Partial<{ title: string; content: string; is_pinned: boolean; is_archived: boolean }>) =>
    api.patch<Note>(`/api/notes/${id}`, data).then(r => r.data),

  remove: (id: number, permanent = false) =>
    api.delete(`/api/notes/${id}`, { params: { permanent } }).then(r => r.data),

  restore: (id: number) => api.post<Note>(`/api/notes/${id}/restore`).then(r => r.data),
}
