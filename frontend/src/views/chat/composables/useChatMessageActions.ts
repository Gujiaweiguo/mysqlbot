import { nextTick, type ComputedRef, type Ref } from 'vue'

import { ChatInfo, ChatRecord } from '@/api/chat'
import type { ChatMessage } from '@/api/chat'

interface UseChatMessageActionsOptions {
  inputMessage: Ref<string>
  loading: Ref<boolean>
  isTyping: Ref<boolean>
  currentChat: Ref<ChatInfo>
  currentChatId: Ref<number | undefined>
  isCompletePage: ComputedRef<boolean>
  innerRef: Ref<HTMLElement | undefined>
  startAutoScroll: () => void
  assistantPrepareSend: () => Promise<void>
  runChartAnswer: (index: number) => Promise<void>
  runAnalysisAnswer: (index: number) => Promise<void>
  runPredictAnswer: (index: number) => Promise<void>
}

export const useChatMessageActions = (options: UseChatMessageActionsOptions) => {
  const sendMessage = async (
    regenerateRecordId: number | undefined = undefined,
    event: { isComposing?: boolean } = {}
  ) => {
    if (event?.isComposing) {
      return
    }

    if (!options.inputMessage.value.trim()) {
      return
    }

    options.loading.value = true
    options.isTyping.value = true

    if (options.isCompletePage.value && options.innerRef.value) {
      options.startAutoScroll()
    }

    await options.assistantPrepareSend()

    const currentRecord = new ChatRecord()
    currentRecord.create_time = new Date()
    currentRecord.chat_id = options.currentChatId.value
    currentRecord.question = options.inputMessage.value
    currentRecord.regenerate_record_id = regenerateRecordId
    currentRecord.sql_answer = ''
    currentRecord.sql = ''
    currentRecord.chart_answer = ''
    currentRecord.chart = ''

    options.currentChat.value.records.push(currentRecord)
    options.inputMessage.value = ''

    await nextTick(async () => {
      if (!options.isCompletePage.value && options.innerRef.value) {
        options.startAutoScroll()
      }

      const index = options.currentChat.value.records.length - 1
      await options.runChartAnswer(index)
    })
  }

  const askAgain = (message: ChatMessage) => {
    if (message.record?.question?.trim() === '') {
      return
    }

    options.inputMessage.value = '/regenerate'
    let regenerateRecordId = message.record?.id
    if (message.record?.id == undefined && message.record?.regenerate_record_id) {
      regenerateRecordId = message.record.regenerate_record_id
    }
    if (regenerateRecordId) {
      options.inputMessage.value = `${options.inputMessage.value} ${regenerateRecordId}`
    }

    void nextTick(() => {
      void sendMessage(regenerateRecordId)
    })
  }

  const clickAnalysis = async (id?: number) => {
    const baseRecord = options.currentChat.value.records.find((value) => id === value.id)
    if (!baseRecord) {
      return
    }

    options.loading.value = true
    options.isTyping.value = true

    const currentRecord = new ChatRecord()
    currentRecord.create_time = new Date()
    currentRecord.chat_id = baseRecord.chat_id
    currentRecord.question = baseRecord.question
    currentRecord.chart = baseRecord.chart
    currentRecord.data = baseRecord.data
    currentRecord.analysis_record_id = id
    currentRecord.analysis = ''

    options.currentChat.value.records.push(currentRecord)

    await nextTick(async () => {
      const index = options.currentChat.value.records.length - 1
      await options.runAnalysisAnswer(index)
    })
  }

  const clickPredict = async (id?: number) => {
    const baseRecord = options.currentChat.value.records.find((value) => id === value.id)
    if (!baseRecord) {
      return
    }

    options.loading.value = true
    options.isTyping.value = true

    const currentRecord = new ChatRecord()
    currentRecord.create_time = new Date()
    currentRecord.chat_id = baseRecord.chat_id
    currentRecord.question = baseRecord.question
    currentRecord.chart = baseRecord.chart
    currentRecord.data = baseRecord.data
    currentRecord.predict_record_id = id
    currentRecord.predict = ''
    currentRecord.predict_data = ''

    options.currentChat.value.records.push(currentRecord)

    await nextTick(async () => {
      const index = options.currentChat.value.records.length - 1
      await options.runPredictAnswer(index)
    })
  }

  return {
    askAgain,
    clickAnalysis,
    clickPredict,
    sendMessage,
  }
}
