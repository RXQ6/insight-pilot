import { api } from './client'
import type { Dataset, PreviewResponse } from '../types'

export const datasetApi = {
  list: () => api.get<{ items: Dataset[] }>('/datasets').then((r) => r.data.items),
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    form.append('name', file.name.replace(/\.csv$/i, ''))
    return api.post<Dataset>('/datasets/upload', form)
  },
  preview: (id: number) => api.get<PreviewResponse>(`/datasets/${id}/preview`).then((r) => r.data),
  remove: (id: number) => api.delete(`/datasets/${id}`),
}