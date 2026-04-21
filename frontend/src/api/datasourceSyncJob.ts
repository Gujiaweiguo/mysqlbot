import { request } from '@/utils/request'

export interface DatasourceSyncJobSubmitRequest {
  datasource_id: number
  tables: string[]
}

export interface DatasourceSyncJobBase {
  job_id: number
  datasource_id: number
  status: string
}

export interface DatasourceSyncJobSubmitResponse extends DatasourceSyncJobBase {
  phase: string | null
  reused_active_job: boolean
}

export interface DatasourceSyncJobSummary extends DatasourceSyncJobBase {
  total_tables: number
  completed_tables: number
  failed_tables: number
  skipped_tables: number
  create_time: string
  finish_time: string | null
}

export interface DatasourceSyncJobStatusResponse extends DatasourceSyncJobSummary {
  phase: string | null
  total_fields: number
  completed_fields: number
  current_table_name: string | null
  embedding_followup_status: string | null
  error_summary: string | null
  update_time: string
  start_time: string | null
  finish_time: string | null
}

export type DatasourceSyncJobRecord = Partial<
  DatasourceSyncJobSubmitResponse & DatasourceSyncJobSummary & DatasourceSyncJobStatusResponse
> &
  DatasourceSyncJobBase

const syncJobRequestConfig = {
  requestOptions: {
    customError: true,
  },
}

export const datasourceSyncJobApi = {
  submitJob: (data: DatasourceSyncJobSubmitRequest) =>
    request.post<DatasourceSyncJobSubmitResponse>('/sync-jobs', data, syncJobRequestConfig),
  listJobs: (datasourceId: number) =>
    request.get<DatasourceSyncJobSummary[]>(`/sync-jobs?datasource_id=${datasourceId}`, syncJobRequestConfig),
  getJobStatus: (jobId: number) =>
    request.get<DatasourceSyncJobStatusResponse>(`/sync-jobs/${jobId}`, syncJobRequestConfig),
  cancelJob: (jobId: number) =>
    request.post<DatasourceSyncJobStatusResponse>(`/sync-jobs/${jobId}/cancel`, undefined, syncJobRequestConfig),
}
