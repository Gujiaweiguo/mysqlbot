<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus-secondary'
import { embeddingApi } from '@/api/embedding'
import { useI18n } from 'vue-i18n'
import { supplierList } from '@/entity/supplier'

type EmbeddingState =
  | 'disabled'
  | 'configured_unverified'
  | 'validated_disabled'
  | 'enabled'
  | 'reindex_required'
  | 'validation_failed'

type EmbeddingProviderType = 'openai_compatible' | 'local' | 'tencent_cloud'

interface EmbeddingModelOption {
  name: string
}

const OPENAI_COMPATIBLE_SUPPLIER_IDS = [1, 3, 10, 15]
const TENCENT_CLOUD_SUPPLIER_ID = 9

const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const toggling = ref(false)
const modelLoading = ref(false)
const modelOptions = ref<EmbeddingModelOption[]>([])
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
  startup_backfill_policy: 'deferred' as const,
  tencent_secret_id: '',
  tencent_secret_key: '',
  tencent_secret_key_configured: false,
  tencent_region: 'ap-guangzhou',
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
const providerIsTencentCloud = computed(
  () => form.provider_type === 'tencent_cloud'
)
const canEnable = computed(
  () => status.state === 'validated_disabled' && !status.reindex_required
)

const filteredSuppliers = computed(() =>
  supplierList.filter((s) => OPENAI_COMPATIBLE_SUPPLIER_IDS.includes(s.id))
)

const tencentCloudSupplier = computed(() =>
  supplierList.find((s) => s.id === TENCENT_CLOUD_SUPPLIER_ID)
)

const TENCENT_CLOUD_REGIONS = [
  { value: 'ap-guangzhou', label: '广州' },
  { value: 'ap-shanghai', label: '上海' },
  { value: 'ap-beijing', label: '北京' },
  { value: 'ap-chengdu', label: '成都' },
  { value: 'ap-hongkong', label: '香港' },
]

const stateLabelMap: Record<EmbeddingState, string> = {
  disabled: t('model.embedding_state_disabled'),
  configured_unverified: t('model.embedding_state_configured_unverified'),
  validated_disabled: t('model.embedding_state_validated_disabled'),
  enabled: t('model.embedding_state_enabled'),
  reindex_required: t('model.embedding_state_reindex_required'),
  validation_failed: t('model.embedding_state_validation_failed'),
}

const fetchModels = async () => {
  if (!form.supplier_id && form.provider_type !== 'tencent_cloud') {
    modelOptions.value = []
    return
  }
  modelLoading.value = true
  try {
    const supplierId = form.provider_type === 'tencent_cloud' ? TENCENT_CLOUD_SUPPLIER_ID : form.supplier_id
    if (supplierId) {
      const res = await embeddingApi.getModels(supplierId)
      modelOptions.value = res.models || []
    }
  } catch {
    modelOptions.value = []
  } finally {
    modelLoading.value = false
  }
}

watch(
  () => form.supplier_id,
  (newSupplierId) => {
    if (form.provider_type !== 'openai_compatible') return
    const supplier = supplierList.find((s) => s.id === newSupplierId)
    if (supplier) {
      const config = supplier.model_config[0]
      if (config) {
        form.base_url = config.api_domain
      }
    }
    fetchModels()
  }
)

watch(
  () => form.provider_type,
  (newType) => {
    if (newType === 'local') {
      form.supplier_id = null
      form.base_url = ''
      form.model_name = ''
      modelOptions.value = []
    } else if (newType === 'tencent_cloud') {
      form.supplier_id = null
      form.base_url = ''
      fetchModels()
    } else if (!form.supplier_id) {
      form.supplier_id = 15
      const supplier = supplierList.find((s) => s.id === 15)
      if (supplier) {
        const config = supplier.model_config[0]
        if (config) {
          form.base_url = config.api_domain
        }
      }
      fetchModels()
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
    form.tencent_secret_id = config.tencent_secret_id || ''
    form.tencent_secret_key = config.tencent_secret_key || ''
    form.tencent_secret_key_configured = config.tencent_secret_key_configured || false
    form.tencent_region = config.tencent_region || 'ap-guangzhou'
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
      tencent_secret_id: null,
      tencent_secret_key: '',
      tencent_secret_key_configured: false,
      tencent_region: 'ap-guangzhou',
    }
  }
  if (form.provider_type === 'tencent_cloud') {
    return {
      provider_type: 'tencent_cloud',
      supplier_id: TENCENT_CLOUD_SUPPLIER_ID,
      model_name: form.model_name || null,
      base_url: null,
      api_key: '',
      api_key_configured: false,
      timeout_seconds: 30,
      local_model: null,
      startup_backfill_policy: form.startup_backfill_policy,
      tencent_secret_id: form.tencent_secret_id || null,
      tencent_secret_key: form.tencent_secret_key,
      tencent_secret_key_configured: !!form.tencent_secret_key || form.tencent_secret_key_configured,
      tencent_region: form.tencent_region,
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
    tencent_secret_id: null,
    tencent_secret_key: '',
    tencent_secret_key_configured: false,
    tencent_region: 'ap-guangzhou',
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
    form.tencent_secret_id = config.tencent_secret_id || ''
    form.tencent_secret_key = config.tencent_secret_key || ''
    form.tencent_secret_key_configured = config.tencent_secret_key_configured || false
    form.tencent_region = config.tencent_region || 'ap-guangzhou'
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
          <el-option
            :label="t('model.embedding_provider_tencent_cloud')"
            value="tencent_cloud"
          />
          <el-option :label="t('model.embedding_provider_local')" value="local" />
        </el-select>
      </el-form-item>

      <template v-if="providerIsOpenAICompatible">
        <el-form-item :label="t('model.embedding_supplier')">
          <el-select v-model="form.supplier_id" style="width: 100%" filterable>
            <el-option
              v-for="supplier in filteredSuppliers"
              :key="supplier.id"
              :label="t(supplier.i18nKey)"
              :value="supplier.id"
            >
              <div style="display: flex; align-items: center; gap: 8px">
                <img :src="supplier.icon" width="20" height="20" style="border-radius: 4px" />
                <span>{{ t(supplier.i18nKey) }}</span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>

        <el-form-item :label="t('model.embedding_base_url')">
          <el-input
            v-model="form.base_url"
            :placeholder="t('model.embedding_base_url_placeholder')"
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_model_name')">
          <el-select
            v-model="form.model_name"
            :placeholder="t('model.embedding_model_name_placeholder')"
            filterable
            allow-create
            :loading="modelLoading"
            style="width: 100%"
          >
            <el-option
              v-for="item in modelOptions"
              :key="item.name"
              :label="item.name"
              :value="item.name"
            />
          </el-select>
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

      <template v-else-if="providerIsTencentCloud">
        <el-form-item :label="t('model.embedding_supplier')">
          <div v-if="tencentCloudSupplier" style="display: flex; align-items: center; gap: 8px">
            <img
              :src="tencentCloudSupplier.icon"
              width="20"
              height="20"
              style="border-radius: 4px"
            />
            <span>{{ t(tencentCloudSupplier.i18nKey) }}</span>
          </div>
        </el-form-item>

        <el-form-item :label="t('model.embedding_tencent_secret_id')">
          <el-input
            v-model="form.tencent_secret_id"
            :placeholder="t('model.embedding_tencent_secret_id_placeholder')"
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_tencent_secret_key')">
          <el-input
            v-model="form.tencent_secret_key"
            type="password"
            show-password
            :placeholder="
              form.tencent_secret_key_configured
                ? t('model.embedding_tencent_secret_key_keep_placeholder')
                : ''
            "
          />
        </el-form-item>

        <el-form-item :label="t('model.embedding_tencent_region')">
          <el-select v-model="form.tencent_region" style="width: 100%">
            <el-option
              v-for="region in TENCENT_CLOUD_REGIONS"
              :key="region.value"
              :label="region.label"
              :value="region.value"
            />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('model.embedding_model_name')">
          <el-select
            v-model="form.model_name"
            :placeholder="t('model.embedding_model_name_placeholder')"
            filterable
            allow-create
            :loading="modelLoading"
            style="width: 100%"
          >
            <el-option
              v-for="item in modelOptions"
              :key="item.name"
              :label="item.name"
              :value="item.name"
            />
          </el-select>
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
