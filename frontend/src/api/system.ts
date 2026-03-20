import { request } from '@/utils/request'
import { sqlbotEncrypt } from '@/xpack-compat'

export const modelApi = {
  queryAll: (keyword?: string) =>
    request.get('/system/aimodel', { params: keyword ? { keyword } : {} }),
  add: (data: any) => {
    const param = {
      ...data,
      config_list: Array.isArray(data.config_list)
        ? data.config_list.map((item: any) => ({ ...item }))
        : data.config_list,
    }
    if (param.api_key) {
      param.api_key = sqlbotEncrypt(data.api_key)
    }
    if (param.api_domain) {
      param.api_domain = sqlbotEncrypt(data.api_domain)
    }
    return request.post('/system/aimodel', param)
  },
  edit: (data: any) => {
    const param = {
      ...data,
      config_list: Array.isArray(data.config_list)
        ? data.config_list.map((item: any) => ({ ...item }))
        : data.config_list,
    }
    if (param.api_key) {
      param.api_key = sqlbotEncrypt(data.api_key)
    }
    if (param.api_domain) {
      param.api_domain = sqlbotEncrypt(data.api_domain)
    }
    return request.put('/system/aimodel', param)
  },
  delete: (id: number) => request.delete(`/system/aimodel/${id}`),
  query: (id: number) => request.get(`/system/aimodel/${id}`),
  setDefault: (id: number) => request.put(`/system/aimodel/default/${id}`),
  check: (data: any) => request.fetchStream('/system/aimodel/status', data),
  platform: (id: number) => request.get(`/system/platform/org/${id}`),
  userSync: (data: any) => request.post(`/system/platform/user/sync`, data),
}
