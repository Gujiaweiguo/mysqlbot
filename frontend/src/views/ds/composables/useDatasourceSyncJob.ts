import { computed, onBeforeUnmount, ref } from 'vue'
import { request } from '@/utils/request'
import {
  datasourceSyncJobApi,
  type DatasourceSyncJobRecord,
  type DatasourceSyncJobStatusResponse,
} from '@/api/datasourceSyncJob'

const ACTIVE_SYNC_JOB_STATUSES = new Set(['pending', 'running', 'finalizing'])
const TERMINAL_SYNC_JOB_STATUSES = new Set(['succeeded', 'failed', 'partial', 'cancelled'])

export interface TrackedDatasourceSyncJob extends DatasourceSyncJobRecord {
  restored?: boolean
}

interface StartTrackingOptions {
  restored?: boolean
  showError?: boolean
}

interface UseDatasourceSyncJobOptions {
  pollInterval?: number
  onTerminal?: (job: TrackedDatasourceSyncJob, previousStatus?: string | null) => void
}

const normalizeSyncJobStatus = (status?: string | null) => status?.toString().trim().toLowerCase() ?? ''

const isActiveSyncJobStatus = (status?: string | null) =>
  ACTIVE_SYNC_JOB_STATUSES.has(normalizeSyncJobStatus(status))

const isTerminalSyncJobStatus = (status?: string | null) =>
  TERMINAL_SYNC_JOB_STATUSES.has(normalizeSyncJobStatus(status))

export const useDatasourceSyncJob = (options: UseDatasourceSyncJobOptions = {}) => {
  const pollInterval = options.pollInterval ?? 2000

  const job = ref<TrackedDatasourceSyncJob | null>(null)
  const dialogVisible = ref(false)
  const isPolling = ref(false)
  const isRestoring = ref(false)
  const isCancelling = ref(false)
  const requestError = ref('')
  const pollTimer = ref<number | null>(null)

  const stopPolling = () => {
    if (pollTimer.value !== null) {
      window.clearTimeout(pollTimer.value)
      pollTimer.value = null
    }
    isPolling.value = false
  }

  const setJob = (nextJob: DatasourceSyncJobRecord, trackedOptions: StartTrackingOptions = {}) => {
    job.value = {
      ...(job.value ?? {}),
      ...nextJob,
      restored: trackedOptions.restored ?? job.value?.restored ?? false,
    }
  }

  const schedulePoll = (jobId: number) => {
    stopPolling()
    pollTimer.value = window.setTimeout(() => {
      void pollJob(jobId)
    }, pollInterval)
  }

  const handleRequestError = async (error: unknown, showError = false) => {
    requestError.value = await request.extractErrorMessage(error)
    if (showError) {
      await request.showError(error)
    }
  }

  const pollJob = async (jobId: number, showError = false) => {
    isPolling.value = true
    try {
      const previousStatus = job.value?.status ?? null
      const detail = await datasourceSyncJobApi.getJobStatus(jobId)

      if (job.value?.job_id && job.value.job_id !== jobId) {
        return
      }

      requestError.value = ''
      setJob(detail)

      if (isActiveSyncJobStatus(detail.status)) {
        schedulePoll(jobId)
        return
      }

      stopPolling()
      options.onTerminal?.(job.value as TrackedDatasourceSyncJob, previousStatus)
    } catch (error) {
      stopPolling()
      await handleRequestError(error, showError)
    } finally {
      isPolling.value = false
    }
  }

  const startTracking = async (
    nextJob: DatasourceSyncJobRecord,
    trackedOptions: StartTrackingOptions = {}
  ) => {
    if (!nextJob.job_id) {
      return
    }

    dialogVisible.value = true
    requestError.value = ''
    stopPolling()
    setJob(nextJob, trackedOptions)
    await pollJob(nextJob.job_id, trackedOptions.showError ?? false)
  }

  const restoreLatestJob = async (datasourceId: number) => {
    isRestoring.value = true
    try {
      const jobs = await datasourceSyncJobApi.listJobs(datasourceId)
      const activeJob = jobs.find((item) => isActiveSyncJobStatus(item.status))

      if (!activeJob) {
        job.value = null
        dialogVisible.value = false
        requestError.value = ''
        stopPolling()
        return null
      }

      await startTracking(activeJob, { restored: true })
      return activeJob
    } catch (error) {
      await handleRequestError(error)
      return null
    } finally {
      isRestoring.value = false
    }
  }

  const cancelJob = async () => {
    if (!job.value?.job_id || isCancelling.value) {
      return null
    }

    isCancelling.value = true
    try {
      const previousStatus = job.value.status ?? null
      const detail = await datasourceSyncJobApi.cancelJob(job.value.job_id)
      requestError.value = ''
      stopPolling()
      setJob(detail)
      options.onTerminal?.(job.value as TrackedDatasourceSyncJob, previousStatus)
      return detail
    } catch (error) {
      await handleRequestError(error, true)
      return null
    } finally {
      isCancelling.value = false
    }
  }

  const closeDialog = () => {
    if (isActive.value && !requestError.value) {
      return
    }
    dialogVisible.value = false
  }

  const reset = () => {
    stopPolling()
    job.value = null
    dialogVisible.value = false
    isCancelling.value = false
    isRestoring.value = false
    requestError.value = ''
  }

  const isActive = computed(() => isActiveSyncJobStatus(job.value?.status))
  const isTerminal = computed(() => isTerminalSyncJobStatus(job.value?.status))
  const isSucceeded = computed(() => normalizeSyncJobStatus(job.value?.status) === 'succeeded')
  const isFailed = computed(() => normalizeSyncJobStatus(job.value?.status) === 'failed')
  const isCancelled = computed(() => normalizeSyncJobStatus(job.value?.status) === 'cancelled')
  const isPartial = computed(() => normalizeSyncJobStatus(job.value?.status) === 'partial')

  const completedTables = computed(() => job.value?.completed_tables ?? 0)
  const failedTables = computed(() => job.value?.failed_tables ?? 0)
  const skippedTables = computed(() => job.value?.skipped_tables ?? 0)
  const totalTables = computed(() => job.value?.total_tables ?? 0)
  const completedFields = computed(() => job.value?.completed_fields ?? 0)
  const totalFields = computed(() => job.value?.total_fields ?? 0)
  const processedTables = computed(
    () => completedTables.value + failedTables.value + skippedTables.value
  )

  const progressPercent = computed(() => {
    if (!job.value) {
      return 0
    }

    if (isSucceeded.value || isPartial.value) {
      return 100
    }

    if (totalTables.value > 0) {
      return Math.min(100, Math.round((processedTables.value / totalTables.value) * 100))
    }

    if (totalFields.value > 0) {
      return Math.min(100, Math.round((completedFields.value / totalFields.value) * 100))
    }

    return isActive.value ? 5 : 0
  })

  const failureDetails = computed(() => {
    const summary = job.value?.error_summary
    if (!summary) {
      return []
    }

    return summary
      .split(/\n|;/)
      .map((item) => item.trim())
      .filter(Boolean)
  })

  onBeforeUnmount(() => {
    stopPolling()
  })

  return {
    job,
    dialogVisible,
    isPolling,
    isRestoring,
    isCancelling,
    requestError,
    isActive,
    isTerminal,
    isSucceeded,
    isFailed,
    isCancelled,
    isPartial,
    progressPercent,
    failureDetails,
    startTracking,
    restoreLatestJob,
    cancelJob,
    closeDialog,
    reset,
  }
}

export type { DatasourceSyncJobStatusResponse }
