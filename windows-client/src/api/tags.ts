/** Tags API */
import api from './index'

export interface Tag {
  id: number
  name: string
  note_count?: number
}

export const tagsApi = {
  list: () => api.get<Tag[]>('/api/tags').then(r => r.data),

  create: (name: string) =>
    api.post<Tag>('/api/tags', null, { params: { name } }).then(r => r.data),

  remove: (id: number) => api.delete(`/api/tags/${id}`).then(r => r.data),

  getNoteTags: (noteId: number) =>
    api.get<Tag[]>(`/api/tags/by-note/${noteId}`).then(r => r.data),

  setNoteTags: (noteId: number, tagNames: string[]) =>
    api.put(`/api/tags/by-note/${noteId}`, tagNames).then(r => r.data),
}
