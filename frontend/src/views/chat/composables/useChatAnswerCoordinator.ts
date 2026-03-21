import type { Ref } from 'vue'

type ChatAnswerHandle = {
  index?: () => number
  id?: () => number | undefined
  stop: () => void
  sendMessage?: () => Promise<void>
  getRecommendQuestions?: () => void | Promise<void>
}

const toHandles = (value: ChatAnswerHandle | ChatAnswerHandle[] | undefined): ChatAnswerHandle[] => {
  if (!value) {
    return []
  }
  return Array.isArray(value) ? value : [value]
}

const runMatchingHandle = async (
  handles: ChatAnswerHandle[],
  matcher: (handle: ChatAnswerHandle) => boolean,
  action: (handle: ChatAnswerHandle) => Promise<void> | void
) => {
  for (const handle of handles) {
    if (matcher(handle)) {
      await action(handle)
      return
    }
  }
}

export const useChatAnswerCoordinator = (
  recommendQuestionRef: Ref<ChatAnswerHandle | ChatAnswerHandle[] | undefined>,
  chartAnswerRef: Ref<ChatAnswerHandle | ChatAnswerHandle[] | undefined>,
  analysisAnswerRef: Ref<ChatAnswerHandle | ChatAnswerHandle[] | undefined>,
  predictAnswerRef: Ref<ChatAnswerHandle | ChatAnswerHandle[] | undefined>
) => {
  const stopAll = () => {
    for (const handle of [
      ...toHandles(recommendQuestionRef.value),
      ...toHandles(chartAnswerRef.value),
      ...toHandles(analysisAnswerRef.value),
      ...toHandles(predictAnswerRef.value),
    ]) {
      handle.stop()
    }
  }

  const getRecommendQuestions = async (recordId?: number) => {
    await runMatchingHandle(
      toHandles(recommendQuestionRef.value),
      (handle) => (handle.id ? handle.id() === recordId : true),
      async (handle) => {
        await handle.getRecommendQuestions?.()
      }
    )
  }

  const runChartAnswer = async (index: number) => {
    await runMatchingHandle(
      toHandles(chartAnswerRef.value),
      (handle) => (handle.index ? handle.index() === index : true),
      async (handle) => {
        await handle.sendMessage?.()
      }
    )
  }

  const runAnalysisAnswer = async (index: number) => {
    await runMatchingHandle(
      toHandles(analysisAnswerRef.value),
      (handle) => (handle.index ? handle.index() === index : true),
      async (handle) => {
        await handle.sendMessage?.()
      }
    )
  }

  const runPredictAnswer = async (index: number) => {
    await runMatchingHandle(
      toHandles(predictAnswerRef.value),
      (handle) => (handle.index ? handle.index() === index : true),
      async (handle) => {
        await handle.sendMessage?.()
      }
    )
  }

  return {
    getRecommendQuestions,
    runAnalysisAnswer,
    runChartAnswer,
    runPredictAnswer,
    stopAll,
  }
}
