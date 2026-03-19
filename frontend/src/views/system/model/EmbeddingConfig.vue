<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus-secondary'
import { embeddingApi } from '@/api/embedding'

type EmbeddingState =
  | 'disabled'
  | 'configured_unverified'
  | 'validated_disabled'
  | 'enabled'
  | 'reindex_required'
  | 'validation_failed'

const loading = ref(false)
const saving = ref(false)
const validating = ref(false)
const toggling = ref(false)

const form = reactive({
  provider: 'remote',
  remote_base_url: '',
  remote_api_key: '',
  remote_api_key_configured: false,
  remote_model: '',
  remote_timeout_seconds: 30,
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

const providerIsRemote = computed(() => form.provider === 'remote')
const canEnable = computed(
  () => status.state === 'validated_disabled' && !status.reindex_required
)

const stateLabelMap: Record<EmbeddingState, string> = {
  disabled: 'Disabled',
  configured_unverified: 'Configured, validation required',
  validated_disabled: 'Validated, not enabled',
  enabled: 'Enabled',
  reindex_required: 'Reindex required',
  validation_failed: 'Validation failed',
}

const loadConfig = async () => {
  loading.value = true
  try {
    const res: any = await embeddingApi.getConfig()
    Object.assign(form, res.config)
    Object.assign(status, res.status)
  } finally {
    loading.value = false
  }
}

const saveConfig = async () => {
  saving.value = true
  try {
    const res: any = await embeddingApi.saveConfig({ config: { ...form } })
    Object.assign(form, res.config)
    Object.assign(status, res.status)
    ElMessage.success('Embedding configuration saved')
  } finally {
    saving.value = false
  }
}

const validateConfig = async () => {
  validating.value = true
  try {
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
      ElMessage.error(res.message)
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
      <div class="title">Embedding Configuration</div>
      <div class="status-row">
        <el-tag>{{ stateLabelMap[status.state] }}</el-tag>
        <el-tag :type="status.enabled ? 'success' : 'info'">
          {{ status.enabled ? 'Enabled' : 'Disabled' }}
        </el-tag>
      </div>
      <div class="hint">{{ status.last_validation.message }}</div>
      <div v-if="status.last_validation.at" class="hint small">
        Last validation: {{ status.last_validation.at }}
      </div>
      <div v-if="status.reindex_required" class="warning">
        {{ status.reindex_reason || 'Re-embedding may be required before safe enablement.' }}
      </div>
    </div>

    <el-form label-position="top" class="config-form">
      <el-form-item label="Provider">
        <el-select v-model="form.provider" style="width: 100%">
          <el-option label="Remote" value="remote" />
          <el-option label="Local" value="local" />
        </el-select>
      </el-form-item>

      <template v-if="providerIsRemote">
        <el-form-item label="Remote Base URL">
          <el-input v-model="form.remote_base_url" placeholder="http://embedding-service/v1" />
        </el-form-item>
        <el-form-item label="Remote API Key">
          <el-input
            v-model="form.remote_api_key"
            type="password"
            show-password
            :placeholder="form.remote_api_key_configured ? 'Configured (leave empty to keep current key)' : ''"
          />
        </el-form-item>
        <el-form-item label="Remote Model">
          <el-input v-model="form.remote_model" placeholder="text-embedding-3-small" />
        </el-form-item>
        <el-form-item label="Remote Timeout Seconds">
          <el-input-number v-model="form.remote_timeout_seconds" :min="1" :max="300" />
        </el-form-item>
      </template>

      <template v-else>
        <el-form-item label="Local Model">
          <el-input v-model="form.local_model" placeholder="shibing624/text2vec-base-chinese" />
        </el-form-item>
      </template>

      <el-form-item label="Startup Backfill Policy">
        <el-select v-model="form.startup_backfill_policy" style="width: 100%">
          <el-option label="Eager" value="eager" />
          <el-option label="Deferred" value="deferred" />
          <el-option label="Manual" value="manual" />
        </el-select>
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button type="primary" :loading="saving" @click="saveConfig">Save Configuration</el-button>
      <el-button secondary :loading="validating" @click="validateConfig"
        >Validate Configuration</el-button
      >
      <el-button type="success" :disabled="!canEnable" :loading="toggling" @click="enableEmbedding"
        >Enable Embedding</el-button
      >
      <el-button secondary :disabled="!status.enabled" :loading="toggling" @click="disableEmbedding"
        >Disable Embedding</el-button
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
