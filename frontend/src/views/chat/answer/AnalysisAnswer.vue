<script setup lang="ts">
import BaseAnswer from './BaseAnswer.vue'
import { chatApi, ChatInfo, type ChatMessage, ChatRecord } from '@/api/chat.ts'
import { computed, nextTick, onBeforeUnmount, ref } from 'vue'
import MdComponent from '@/views/chat/component/MdComponent.vue'
import { consumeChatStream, type ChatStreamPayload } from '@/views/chat/composables/useChatStream'
const props = withDefaults(
  defineProps<{
    chatList?: Array<ChatInfo>
    currentChatId?: number
    currentChat?: ChatInfo
    message?: ChatMessage
    loading?: boolean
  }>(),
  {
    chatList: () => [],
    currentChatId: undefined,
    currentChat: () => new ChatInfo(),
    message: undefined,
    loading: false,
  }
)

const emits = defineEmits([
  'finish',
  'error',
  'stop',
  'update:loading',
  'update:chatList',
  'update:currentChat',
  'update:currentChatId',
])

const index = computed(() => {
  if (props.message?.index) {
    return props.message.index
  }
  if (props.message?.index === 0) {
    return 0
  }
  return -1
})

const _currentChatId = computed({
  get() {
    return props.currentChatId
  },
  set(v) {
    emits('update:currentChatId', v)
  },
})

const _currentChat = computed({
  get() {
    return props.currentChat
  },
  set(v) {
    emits('update:currentChat', v)
  },
})

const _chatList = computed({
  get() {
    return props.chatList
  },
  set(v) {
    emits('update:chatList', v)
  },
})

const _loading = computed({
  get() {
    return props.loading
  },
  set(v) {
    emits('update:loading', v)
  },
})

const stopFlag = ref(false)
const sendMessage = async () => {
  stopFlag.value = false
  _loading.value = true

  if (index.value < 0) {
    _loading.value = false
    return
  }

  const currentRecord: ChatRecord = _currentChat.value.records[index.value]

  let error: boolean = false
  if (_currentChatId.value === undefined || currentRecord.analysis_record_id === undefined) {
    error = true
  }
  if (error) return

  try {
    const controller: AbortController = new AbortController()
    let analysis_answer = ''
    let analysis_answer_thinking = ''
    const response = await chatApi.analysis(currentRecord.analysis_record_id, controller)

    await consumeChatStream<ChatStreamPayload>({
      response,
      controller,
      isStopped: () => stopFlag.value,
      onMessageError: (message) => {
        ElMessage({
          message,
          type: 'error',
          showClose: true,
        })
      },
      onEvent: async (data) => {
        switch (data.type) {
          case 'id':
            currentRecord.id = data.id as number | undefined
            _currentChat.value.records[index.value].id = data.id as number | undefined
            break
          case 'info':
            console.info(data.msg)
            break
          case 'error':
            currentRecord.error = String(data.content ?? '')
            emits('error', currentRecord.id)
            break
          case 'analysis-result':
            analysis_answer += String(data.content ?? '')
            analysis_answer_thinking += String(data.reasoning_content ?? '')
            _currentChat.value.records[index.value].analysis = analysis_answer
            _currentChat.value.records[index.value].analysis_thinking = analysis_answer_thinking
            break
          case 'analysis_finish':
            emits('finish', currentRecord.id)
            break
        }
        await nextTick()
      },
    })
  } catch (error) {
    if (!currentRecord.error) {
      currentRecord.error = ''
    }
    if (currentRecord.error.trim().length !== 0) {
      currentRecord.error = currentRecord.error + '\n'
    }
    currentRecord.error = currentRecord.error + 'Error:' + error
    console.error('Error:', error)
    emits('error')
  } finally {
    _loading.value = false
  }
}
function stop() {
  stopFlag.value = true
  _loading.value = false
  emits('stop')
}

onBeforeUnmount(() => {
  stop()
})
defineExpose({ sendMessage, index: () => index.value, chatList: () => _chatList.value, stop })
</script>

<template>
  <BaseAnswer
    v-if="message"
    :message="message"
    :reasoning-name="['analysis_thinking']"
    :loading="_loading"
  >
    <MdComponent :message="message.record?.analysis" style="margin-top: 12px" />
    <slot></slot>
    <template #tool>
      <slot name="tool"></slot>
    </template>
    <template #footer>
      <slot name="footer"></slot>
    </template>
  </BaseAnswer>
</template>

<style scoped lang="less"></style>
