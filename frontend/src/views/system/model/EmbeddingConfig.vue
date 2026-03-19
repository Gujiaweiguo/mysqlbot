<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus-secondary'
import { embeddingApi } from '@/api/embedding'
import { useI18n } from 'vue-i18n'

type EmbeddingState =
  | 'disabled'
  | 'configured_unverified'
  | 'validated_disabled'
  | 'enabled'
  | 'reindex_required'
  | 'validation_failed'

type EmbeddingProviderType = 'openai_compatible' | 'local'

interface EmbeddingSupplier {
  id: number
  name: string
  i18nKey: string
  base_url: string
}

const SUPPORTED_SUPPLIERS: EmbeddingSupplier[] = [
  {
    id: 1,
    name: '阿里云百炼',
    i18nKey: 'supplier.alibaba_cloud_bailian',
    base_url: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
  },
  {
    id: 3,
    name: 'DeepSeek',
    i18nKey: 'supplier.deepseek',
    base_url: 'https://api.deepseek.com',
  },
  {
    id: 10,
    name: '火山引擎',
    i18nKey: 'supplier.volcano_engine',
    base_url: 'https://ark.cn-beijing.volces.com/api/v3',
  },
  {
    id: 15,
    name: '通用OpenAI',
    i18nKey: 'supplier.generic_openai',
    base_url: 'http://127.0.0.1:8000/v1',
  },
]

const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const toggling = ref(false)
const { t } = useI18n()

const form = reactive({
  provider_type: 'openai_compatible' as EmbeddingProviderType,
  supplier_id: 15 as number | null,
  model_name: '',
  base_url: '',
  api_key: '',
  api_key_configured: false,
  timeout_seconds: 30,
  local_model: '',
  startup_backfill_policy: 'deferred',
})

const status = reactive({
  enabled: false,
  state: 'disabled' as EmbeddingState,
  reindex_required: false,
  reindex_reason: '',
  last_validation: {
    success: false,
    message: 'Not validated yet',
    at: null as string | null,
  },
})

const providerIsOpenAICompatible = computed(
  () => form.provider_type === 'openai_compatible'
)
const canEnable = computed(
  () => status.state === 'validated_disabled' && !status.reindex_required
)

const stateLabelMap: Record<EmbeddingState, string> = {
  disabled: t('model.embedding_state_disabled'),
  configured_unverified: t('model.embedding_state_configured_unverified'),
  validated_disabled: t('model.embedding_state_validated_disabled'),
  enabled: t('model.embedding_state_enabled'),
  reindex_required: t('model.embedding_state_reindex_required'),
  validation_failed: t('model.embedding_state_validation_failed'),
}

watch(
  () => form.supplier_id,
  (newSupplierId) => {
    const supplier = SUPPORTED_SUPPLIERS.find((s) => s.id === newSupplierId)
    if (supplier) {
      form.base_url = supplier.base_url
    }
  }
)

watch(
  () => form.provider_type,
  (newType) => {
    if (newType === 'local') {
      form.supplier_id = null
      form.base_url = ''
      form.model_name = ''
    } else if (!form.supplier_id) {
      form.supplier_id = 15
      const supplier = SUPPORTED_SUPPLIERS.find((s) => s.id === 15)
      if (supplier) {
        form.base_url = supplier.base_url
      }
    }
  }
)

const loadConfig = async () => {
  loading.value = true
  try {
    const res: any = await embeddingApi.getConfig()
    const config = res.config || {}
    form.provider_type = config.provider_type || 'openai_compatible'
    form.supplier_id = config.supplier_id ?? 15
    form.model_name = config.model_name || ''
    form.base_url = config.base_url || ''
    form.api_key = config.api_key || ''
    form.api_key_configured = config.api_key_configured || false
    form.timeout_seconds = config.timeout_seconds || 30
    form.local_model = config.local_model || ''
    form.startup_backfill_policy = config.startup_backfill_policy || 'deferred'
    Object.assign(status, res.status)
  } finally {
    loading.value = false
  }
}

const buildConfigPayload = () => {
  if (form.provider_type === 'local') {
    return {
      provider_type: 'local',
      supplier_id: null,
      model_name: null,
      base_url: null,
      api_key: '',
      api_key_configured: false,
      timeout_seconds: 30,
      local_model: form.local_model || null,
      startup_backfill_policy: form.startup_backfill_policy,
    }
  }
  return {
    provider_type: 'openai_compatible',
    supplier_id: form.supplier_id,
    model_name: form.model_name || null,
    base_url: form.base_url,
    api_key: form.api_key,
    api_key_configured: !!form.api_key || form.api_key_configured,
    timeout_seconds: form.timeout_seconds,
    local_model: null,
    startup_backfill_policy: form.startup_backfill_policy,
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const res: any = await embeddingApi.saveConfig({
      config: buildConfigPayload(),
    })
    const config = res.config || {}
    form.provider_type = config.provider_type || 'openai_compatible'
    form.supplier_id = config.supplier_id ?? 15
    form.model_name = config.model_name || ''
    form.base_url = config.base_url || ''
    form.api_key = config.api_key || ''
    form.api_key_configured = config.api_key_configured || false
    form.timeout_seconds = config.timeout_seconds || 30
    form.local_model = config.local_model || ''
    Object.assign(status, res.status)
    ElMessage.success(t('common.save_success'))
  } finally {
    saving.value = false
  }
}

const validateConfig = async () => {
  validating.value = true
  try {
    const saveRes: any = await embeddingApi.saveConfig({
      config: buildConfigPayload(),
    })
    Object.assign(status, saveRes.status)
    const res: any = await embeddingApi.validateConfig()
    status.state = res.state
    status.enabled = false
    status.last_validation = {
      success: res.success,
      message: res.message,
      at: res.validated_at,
    }
    if (res.success) {
      ElMessage.success(res.message)
    } else {
      ElMessage.error(`${t('model.embedding_validation_failed')}: ${res.message}`)
    }
  } finally {
    validating.value = false
  }
}

const enableEmbedding = async () => {
  toggling.value = true
  try {
    const res: any = await embeddingApi.enable()
    status.state = res.state
    status.enabled = !!res.success && res.state === 'enabled'
    if (res.success) {
      ElMessage.success(res.message || 'Embedding enabled')
    } else {
      ElMessage.error(res.message || 'Embedding enable failed')
    }
  } finally {
    toggling.value = false
  }
}

const disableEmbedding = async () => {
  toggling.value = true
  try {
    const res: any = await embeddingApi.disable()
    status.state = res.state
    status.enabled = false
    ElMessage.success(res.message || 'Embedding disabled')
  } finally {
    toggling.value = false
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<template>
  <div v-loading="loading" class="embedding-config">
    <div class="status-card">
      <div class="title">{{ t('model.embedding_configuration') }}</div>
      <div class="status-row">
        <el-tag>{{ stateLabelMap[status.state] }}</el-tag>
        <el-tag :type="status.enabled ? 'success' : 'info'">
          {{ status.enabled ? t('model.embedding_enabled') : t('model.embedding_disabled') }}
        </el-tag>
      </div>
      <div class="hint">{{ status.last_validation.message }}</div>
      <div v-if="status.last_validation.at" class="hint small">
        {{ t('model.embedding_last_validation') }}: {{ status.last_validation.at }}
      </div>
      <div v-if="status.reindex_required" class="warning">
        {{ status.reindex_reason || t('model.embedding_reindex_required_hint') }}
      </div>
    </div>

    <el-form label-position="top" class="config-form">
      <el-form-item :label="t('model.embedding_provider_type')">
        <el-select v-model="form.provider_type" style="width: 100%">
          <el-option
            :label="t('model.embedding_provider_openai_compatible')"
            value="openai_compatible"
          />
          <el-option :label="t('model.embedding_provider_local')" value="local" />
        </el-select>
      </el-form-item>

      <template v-if="providerIsOpenAICompatible">
        <el-form-item :label="t('model.embedding_supplier')">
          <el-select v-model="form.supplier_id" style="width: 100%">
            <el-option
              v-for="supplier in SUPPORTED_SUPPLIERS"
              :key="supplier.id"
              :label="t(supplier.i18nKey)"
              :value="supplier.id"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('model.embedding_base_url')">
          <el-input
            v-model="form.base_url"
            :placeholder="t('model.embedding_base_url_placeholder')"
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_model_name')">
          <el-input
            v-model="form.model_name"
            :placeholder="t('model.embedding_model_name_placeholder')"
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_api_key')">
          <el-input
            v-model="form.api_key"
            type="password"
            show-password
            :placeholder="
              form.api_key_configured
                ? t('model.embedding_api_key_keep_placeholder')
                : ''
            "
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_timeout_seconds')">
          <el-input-number v-model="form.timeout_seconds" :min="1" :max="300" />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item :label="t('model.embedding_local_model')">
          <el-input
            v-model="form.local_model"
            placeholder="shibing624/text2vec-base-chinese"
          />
        </el-form-item>
      </template>

      <el-form-item :label="t('model.embedding_startup_backfill_policy')">
        <el-select v-model="form.startup_backfill_policy" style="width: 100%">
          <el-option :label="t('model.embedding_backfill_eager')" value="eager" />
          <el-option :label="t('model.embedding_backfill_deferred')" value="deferred" />
          <el-option :label="t('model.embedding_backfill_manual')" value="manual" />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button type="primary" :loading="saving" @click="saveConfig">{{
        t('model.embedding_save_configuration')
      }}</el-button>
      <el-button secondary :loading="validating" @click="validateConfig"
        >{{ t('model.embedding_validate_configuration') }}</el-button
      >
      <el-button
        type="success"
        :disabled="!canEnable"
        :loading="toggling"
        @click="enableEmbedding"
        >{{ t('model.embedding_enable') }}</el-button
      >
      <el-button
        secondary
        :disabled="!status.enabled"
        :loading="toggling"
        @click="disableEmbedding"
        >{{ t('model.embedding_disable') }}</el-button
      >
    </div>
  </div>
</template>

<style scoped lang="less">
.embedding-config {
  padding: 8px 0;

  .status-card {
    border: 1px solid #dee0e3;
    border-radius: 12px;
    background: #fff;
    padding: 16px;
    margin-bottom: 16px;

    .title {
      font-size: 16px;
      font-weight: 500;
      margin-bottom: 8px;
    }

    .status-row {
      display: flex;
      gap: 8px;
      margin-bottom: 8px;
    }

    .hint {
      color: #646a73;
      font-size: 14px;
    }

    .small {
      margin-top: 4px;
      font-size: 12px;
    }

    .warning {
      margin-top: 8px;
      color: #d46b08;
      font-size: 13px;
    }
  }

  .config-form {
    background: #fff;
    border: 1px solid #dee0e3;
    border-radius: 12px;
    padding: 16px;
  }

  .actions {
    margin-top: 16px;
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }
}
</style>
