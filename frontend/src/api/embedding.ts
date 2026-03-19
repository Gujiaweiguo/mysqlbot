import { request } from '@/utils/request'

export const embeddingApi = {
  getConfig: () => request.get('/system/embedding/config'),
  saveConfig: (data: any) => request.put('/system/embedding/config', data),
  validateConfig: (data?: any) =>
    request.post('/system/embedding/validate', data ?? { use_saved_config: true }),
  enable: () => request.post('/system/embedding/enable'),
  disable: () => request.post('/system/embedding/disable'),
}
