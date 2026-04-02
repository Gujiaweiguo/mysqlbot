import { request } from '@/utils/request'

export interface DatasourceSelectedTable {
  table_name: string
  table_comment?: string
}

export interface DatasourceSyncJobStart {
  job_id: number
  datasource_id: number
  status: string
  phase: string
  reused_active_job: boolean
}

export interface DatasourceSyncJob extends DatasourceSyncJobStart {
  total_tables?: number | null
  completed_tables?: number | null
  failed_tables?: number | null
  skipped_tables?: number | null
  total_fields?: number | null
  completed_fields?: number | null
  current_table_name?: string | null
  embedding_followup_status?: string | null
  error_summary?: string | null
  create_time?: string | null
  start_time?: string | null
  finish_time?: string | null
  update_time?: string | null
}

export type DatasourceChooseTablesResult = DatasourceSyncJobStart | null

export const datasourceApi = {
  check: (data: any) => request.post('/datasource/check', data),
  check_by_id: (id: any) => request.get(`/datasource/check/${id}`),
  relationGet: (id: any) => request.post(`/table_relation/get/${id}`),
  relationSave: (dsId: any, data: any) => request.post(`/table_relation/save/${dsId}`, data),
  add: (data: any) => request.post('/datasource/add', data),
  list: () => request.get('/datasource/list'),
  update: (data: any) => request.post('/datasource/update', data),
  delete: (id: number, name: string) => request.post(`/datasource/delete/${id}/${name}`),
  getTables: (id: number) => request.post(`/datasource/getTables/${id}`),
  getTablesByConf: (data: any) => request.post('/datasource/getTablesByConf', data),
  getFields: (id: number, table_name: string) =>
    request.post(`/datasource/getFields/${id}/${table_name}`),
  execSql: (id: number | string, sql: string) =>
    request.post(`/datasource/execSql/${id}`, { sql: sql }),
  chooseTables: (id: number, data: DatasourceSelectedTable[]) =>
    request.post<DatasourceChooseTablesResult>(`/datasource/chooseTables/${id}`, data),
  tableList: (id: number) => request.post(`/datasource/tableList/${id}`),
  fieldList: (id: number, data = { fieldName: '' }) =>
    request.post(`/datasource/fieldList/${id}`, data),
  edit: (data: any) => request.post('/datasource/editLocalComment', data),
  previewData: (id: number, data: any) => request.post(`/datasource/previewData/${id}`, data),
  saveTable: (data: any) => request.post('/datasource/editTable', data),
  saveField: (data: any) => request.post('/datasource/editField', data),
  getDs: (id: number) => request.post(`/datasource/get/${id}`),
  cancelRequests: () => request.cancelRequests(),
  getSchema: (data: any) => request.post('/datasource/getSchemaByConf', data),
  syncFields: (id: number) => request.post(`/datasource/syncFields/${id}`),
  exportDsSchema: (id: any) =>
    request.get(`/datasource/exportDsSchema/${id}`, {
      responseType: 'blob',
      requestOptions: { customError: true },
    }),
  getSyncJob: (jobId: number) => request.get<DatasourceSyncJob>(`/datasource/syncJob/${jobId}`),
  listSyncJobs: (dsId: number) => request.get<DatasourceSyncJob[]>(`/datasource/syncJobs/${dsId}`),
  cancelSyncJob: (jobId: number) =>
    request.post<DatasourceSyncJob>(`/datasource/syncJob/${jobId}/cancel`),
  retrySyncJob: (jobId: number) =>
    request.post<DatasourceSyncJobStart>(`/datasource/syncJob/${jobId}/retry`),
  getSyncJobStreamPath: (jobId: number) => `/datasource/syncJob/${jobId}/stream`,
}
