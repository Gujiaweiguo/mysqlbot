import { request } from '@/utils/request'

export interface EmbeddingModelOption {
  name: string
}

export interface EmbeddingModelsResponse {
  supplier_id: number
  models: EmbeddingModelOption[]
}

export const embeddingApi = {
  getConfig: () => request.get('/system/embedding/config'),
  saveConfig: (data: any) => request.put('/system/embedding/config', data),
  validateConfig: (data?: any) =>
    request.post('/system/embedding/validate', data ?? { use_saved_config: true }),
  enable: (confirmReindex = false) =>
    request.post('/system/embedding/enable', { confirm_reindex: confirmReindex }),
  disable: () => request.post('/system/embedding/disable'),
  getModels: (supplierId: number) =>
    request.get<EmbeddingModelsResponse>('/system/embedding/models', {
      params: { supplier_id: supplierId },
    }),
}
