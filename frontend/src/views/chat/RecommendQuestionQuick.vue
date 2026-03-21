<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, toRefs } from 'vue'
import { endsWith, startsWith } from 'lodash-es'
import { chatApi, ChatInfo } from '@/api/chat.ts'
import { recommendedApi } from '@/api/recommendedApi.ts'
import { consumeChatStream, type ChatStreamPayload } from '@/views/chat/composables/useChatStream'

const props = withDefaults(
  defineProps<{
    recordId?: number
    disabled?: boolean
    datasource?: number
    currentChat?: ChatInfo
  }>(),
  {
    recordId: undefined,
    disabled: false,
    datasource: undefined,
    chatRecommendedQuestions: undefined,
    currentChat: () => new ChatInfo(),
  }
)

const { currentChat } = toRefs(props)

const emits = defineEmits(['clickQuestion', 'stop', 'loadingOver'])

const loading = ref(false)

const questions = ref<string | undefined>('[]')

const computedQuestions = computed<string>(() => {
  if (
    questions.value &&
    questions.value.length > 0 &&
    startsWith(questions.value.trim(), '[') &&
    endsWith(questions.value.trim(), ']')
  ) {
    return JSON.parse(questions.value)
  }
  return []
})

function clickQuestion(question: string): void {
  if (!props.disabled) {
    emits('clickQuestion', question)
  }
}

const stopFlag = ref(false)

async function getRecommendQuestions(articles_number: number, isRetrieve: false) {
  recommendedApi.get_datasource_recommended_base(props.datasource).then((res) => {
    if (res.recommended_config === 2) {
      questions.value = res.questions
    } else if (currentChat.value.recommended_generate && !isRetrieve) {
      questions.value = currentChat.value.recommended_question as string
    } else {
      getRecommendQuestionsLLM(articles_number)
    }
  })
}

async function getRecommendQuestionsLLM(articles_number: number) {
  stopFlag.value = false
  loading.value = true
  try {
    const controller: AbortController = new AbortController()
    const params = articles_number ? '?articles_number=' + articles_number : ''
    const response = await chatApi.recommendQuestions(props.recordId, controller, params)

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
        if (
          data.type === 'recommended_question' &&
          typeof data.content === 'string' &&
          data.content.length > 0 &&
          startsWith(data.content.trim(), '[') &&
          endsWith(data.content.trim(), ']')
        ) {
          questions.value = data.content
          currentChat.value.recommended_question = data.content
          currentChat.value.recommended_generate = true
          await nextTick()
        }
      },
    })
  } finally {
    loading.value = false
    emits('loadingOver')
  }
}

function stop() {
  stopFlag.value = true
  loading.value = false
  emits('stop')
}

onBeforeUnmount(() => {
  stop()
})

defineExpose({ getRecommendQuestions, id: () => props.recordId, stop, getRecommendQuestionsLLM })
</script>

<template>
  <div style="width: 100%; height: 100%">
    <div v-if="computedQuestions.length > 0 || loading" class="recommend-questions">
      <div v-if="loading">
        <el-button style="min-width: unset" type="primary" link loading />
      </div>
      <div v-else class="question-grid-input">
        <div
          v-for="(question, index) in computedQuestions"
          :key="index"
          class="question"
          :class="{ disabled: disabled }"
          :title="question"
          @click="clickQuestion(question)"
        >
          {{ question }}
        </div>
      </div>
    </div>
    <div v-else class="recommend-questions-error">
      {{ $t('qa.retrieve_error') }}
    </div>
  </div>
</template>

<style scoped lang="less">
.recommend-questions {
  width: 100%;
  font-size: 14px;
  font-weight: 500;
  line-height: 22px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  .continue-ask {
    color: rgba(100, 106, 115, 1);
    font-weight: 400;
  }

  .question-grid-input {
    display: grid;
    grid-gap: 1px;
    grid-template-columns: repeat(1, calc(100% - 6px));
  }

  .question-grid {
    display: grid;
    grid-gap: 12px;
    grid-template-columns: repeat(2, calc(50% - 6px));
  }

  .question {
    font-weight: 400;
    cursor: pointer;
    height: 32px;
    border-radius: 4px;
    padding: 5px 8px;
    line-height: 22px;
    white-space: nowrap; /* 禁止换行 */
    overflow: hidden; /* 隐藏溢出内容 */
    text-overflow: ellipsis; /* 显示省略号 */
    &:hover {
      background: rgba(31, 35, 41, 0.1);
    }
    &.disabled {
      cursor: not-allowed;
      background: rgba(245, 246, 247, 1);
    }
  }
}

.recommend-questions-error {
  font-size: 14px;
  font-weight: 400;
  color: rgba(100, 106, 115, 1);
  margin-top: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
}
</style>
