<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue'
import { useClipboard } from '@vueuse/core'
import { useI18n } from 'vue-i18n'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_warning_filled from '@/assets/svg/icon_info_colorful.svg'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import { getOpenClawMcpConfig, type OpenClawMcpConfigResponse } from '@/api/openclaw'

interface DetailItem {
  key: string
  labelKey: string
  value: string
  copyable?: boolean
}

const EMPTY_VALUE = '--'

const { t } = useI18n()
const { copy } = useClipboard({ legacy: true })

const loading = ref(false)
const mcpConfig = ref<OpenClawMcpConfigResponse | null>(null)

const displayValue = (value: string | number | boolean | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return EMPTY_VALUE
  }
  return String(value)
}

const issueList = computed(() => mcpConfig.value?.issues ?? [])
const operationList = computed(() => mcpConfig.value?.operations ?? [])
const toolNameList = computed(() => mcpConfig.value?.tool_names ?? [])

const readyForCopy = computed(() => {
  const current = mcpConfig.value
  if (!current) {
    return false
  }

  return (
    current.ready &&
    current.setup_enabled &&
    Boolean(current.endpoint) &&
    Boolean(current.auth_header) &&
    Boolean(current.auth_scheme)
  )
})

const connectionDetails = computed<DetailItem[]>(() => {
  const current = mcpConfig.value
  if (!current) {
    return []
  }

  return [
    {
      key: 'endpoint',
      labelKey: 'openclaw.endpoint',
      value: displayValue(current.endpoint),
      copyable: true,
    },
    {
      key: 'health_url',
      labelKey: 'openclaw.health_url',
      value: displayValue(current.health_url),
      copyable: true,
    },
    {
      key: 'auth_header',
      labelKey: 'openclaw.auth_header',
      value: displayValue(current.auth_header),
      copyable: true,
    },
    {
      key: 'auth_scheme',
      labelKey: 'openclaw.auth_scheme',
      value: displayValue(current.auth_scheme),
    },
  ]
})

const runtimeDetails = computed<DetailItem[]>(() => {
  const current = mcpConfig.value
  if (!current) {
    return []
  }

  return [
    { key: 'service', labelKey: 'openclaw.service', value: displayValue(current.service) },
    {
      key: 'server_name',
      labelKey: 'openclaw.server_name',
      value: displayValue(current.server_name),
      copyable: true,
    },
    {
      key: 'base_url',
      labelKey: 'openclaw.base_url',
      value: displayValue(current.base_url),
      copyable: true,
    },
    {
      key: 'bind_host',
      labelKey: 'openclaw.bind_host',
      value: displayValue(current.bind_host),
    },
    { key: 'port', labelKey: 'openclaw.port', value: displayValue(current.port) },
    { key: 'path', labelKey: 'openclaw.path', value: displayValue(current.path) },
  ]
})

const configText = computed(() => {
  const current = mcpConfig.value
  if (!current || !readyForCopy.value) {
    return ''
  }

  return JSON.stringify(
    {
      mcp: {
        servers: {
          [current.server_name]: {
            url: current.endpoint,
            headers: {
              [current.auth_header]: `${current.auth_scheme} \${MYSQLBOT_OPENCLAW_TOKEN}`,
            },
          },
        },
      },
    },
    null,
    2
  )
})

const loadData = async () => {
  loading.value = true
  try {
    mcpConfig.value = await getOpenClawMcpConfig()
  } finally {
    loading.value = false
  }
}

const copyValue = async (value: string) => {
  if (!value || value === EMPTY_VALUE) {
    return
  }

  try {
    await copy(value)
    ElMessage.success(t('embedded.copy_successful'))
  } catch {
    ElMessage.error(t('embedded.copy_failed'))
  }
}

const copyConfig = async () => {
  if (!configText.value) {
    return
  }

  try {
    await copy(configText.value)
    ElMessage.success(t('embedded.copy_successful'))
  } catch {
    ElMessage.error(t('embedded.copy_failed'))
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div v-loading="loading" class="openclaw-page">
    <p class="router-title">{{ t('openclaw.title') }}</p>
    <p class="page-description">{{ t('openclaw.description') }}</p>

    <section class="hero-card">
      <div class="hero-card__header">
        <div>
          <p class="hero-card__eyebrow">{{ t('openclaw.assistant_label') }}</p>
          <div class="hero-card__headline">
            <h2>{{ t('openclaw.generated_config') }}</h2>
            <div class="status-pill" :class="readyForCopy ? 'is-ready' : 'is-degraded'">
              <el-icon size="16">
                <SuccessFilled v-if="readyForCopy" />
                <CircleCloseFilled v-else />
              </el-icon>
              <span>{{ t(`openclaw.${readyForCopy ? 'ready' : 'action_required'}`) }}</span>
            </div>
          </div>
          <p class="hero-card__summary">
            {{ t(`openclaw.${readyForCopy ? 'ready_summary' : 'degraded_summary'}`) }}
          </p>
        </div>
      </div>

      <div class="hero-card__stats">
        <div class="hero-stat">
          <span class="hero-stat__label">{{ t('openclaw.service_status') }}</span>
          <span class="hero-stat__value">
            {{ t(`openclaw.${readyForCopy ? 'ready' : 'action_required'}`) }}
          </span>
        </div>
        <div class="hero-stat">
          <span class="hero-stat__label">{{ t('openclaw.setup_enabled') }}</span>
          <span class="hero-stat__value">
            {{ t(`openclaw.${mcpConfig?.setup_enabled ? 'yes' : 'no'}`) }}
          </span>
        </div>
        <div class="hero-stat">
          <span class="hero-stat__label">{{ t('openclaw.issue_count') }}</span>
          <span class="hero-stat__value">{{ issueList.length }}</span>
        </div>
      </div>
    </section>

    <div v-if="issueList.length" class="warn-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="warn-template-content">
        <p class="warn-template-content__title">{{ t('openclaw.warning_title') }}</p>
        <ul class="issue-list">
          <li v-for="issue in issueList" :key="issue">{{ issue }}</li>
        </ul>
      </div>
    </div>

    <div class="card-grid">
      <section class="content-card">
        <div class="content-card__header">
          <div>
            <h3>{{ t('openclaw.connection_settings') }}</h3>
          </div>
        </div>
        <div class="detail-list">
          <div v-for="item in connectionDetails" :key="item.key" class="detail-row">
            <span class="detail-row__label">{{ t(item.labelKey) }}</span>
            <div class="detail-row__value">
              <span>{{ item.value }}</span>
              <el-tooltip
                v-if="item.copyable && item.value !== EMPTY_VALUE"
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="copyValue(item.value)">
                  <icon_copy_outlined />
                </el-icon>
              </el-tooltip>
            </div>
          </div>
        </div>
      </section>

      <section class="content-card">
        <div class="content-card__header">
          <div>
            <h3>{{ t('openclaw.runtime_metadata') }}</h3>
          </div>
        </div>
        <div class="detail-list detail-list--compact">
          <div v-for="item in runtimeDetails" :key="item.key" class="detail-row">
            <span class="detail-row__label">{{ t(item.labelKey) }}</span>
            <div class="detail-row__value">
              <span>{{ item.value }}</span>
              <el-tooltip
                v-if="item.copyable && item.value !== EMPTY_VALUE"
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="copyValue(item.value)">
                  <icon_copy_outlined />
                </el-icon>
              </el-tooltip>
            </div>
          </div>
        </div>

        <div class="tag-section">
          <span class="tag-section__label">{{ t('openclaw.operations') }}</span>
          <div class="tag-list">
            <el-tag v-for="operation in operationList" :key="operation" type="info" effect="plain">
              {{ operation }}
            </el-tag>
          </div>
        </div>

        <div class="tag-section tag-section--last">
          <span class="tag-section__label">{{ t('openclaw.tool_names') }}</span>
          <div class="tag-list">
            <el-tag v-for="toolName in toolNameList" :key="toolName" type="info" effect="plain">
              {{ toolName }}
            </el-tag>
          </div>
        </div>
      </section>
    </div>

    <section class="content-card content-card--full">
      <div class="content-card__header">
        <div>
          <h3>{{ t('openclaw.generated_config') }}</h3>
        </div>
        <el-button v-if="readyForCopy" secondary @click="copyConfig">
          {{ t('datasource.copy') }}
        </el-button>
      </div>

      <template v-if="readyForCopy">
        <div class="config-intro">
          <p class="config-intro__title">{{ t('openclaw.copy_ready_title') }}</p>
          <p class="config-intro__description">{{ t('openclaw.copy_ready_description') }}</p>
        </div>
        <pre class="config-block">{{ configText }}</pre>
      </template>

      <div v-else class="blocked-state">
        <span class="blocked-state__icon">
          <el-icon>
            <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
          </el-icon>
        </span>
        <div>
          <p class="blocked-state__title">{{ t('openclaw.copy_blocked_title') }}</p>
          <p class="blocked-state__description">{{ t('openclaw.copy_blocked_description') }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style lang="less" scoped>
.openclaw-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding-bottom: 24px;

  .router-title {
    color: #1f2329;
    font-feature-settings:
      'clig' off,
      'liga' off;
    font-family: var(--de-custom_font, 'PingFang');
    font-size: 20px;
    font-style: normal;
    font-weight: 500;
    line-height: 28px;
  }

  .page-description {
    margin-top: -8px;
    color: #646a73;
    font-size: 14px;
    line-height: 22px;
  }
}

.hero-card,
.content-card {
  background: var(--ContentBG, #ffffff);
  border: 1px solid #dee0e3;
  border-radius: 12px;
}

.hero-card {
  padding: 20px 24px;
  background:
    linear-gradient(135deg, rgba(28, 186, 144, 0.08), rgba(28, 186, 144, 0) 58%),
    linear-gradient(180deg, #ffffff, #fbfcfc);

  .hero-card__header {
    display: flex;
    justify-content: space-between;
    gap: 16px;
  }

  .hero-card__eyebrow {
    color: var(--ed-color-primary);
    font-size: 12px;
    font-weight: 500;
    letter-spacing: 0.08em;
    line-height: 20px;
    text-transform: uppercase;
  }

  .hero-card__headline {
    margin-top: 4px;
    display: flex;
    align-items: center;
    gap: 12px;
    flex-wrap: wrap;

    h2 {
      color: #1f2329;
      font-size: 18px;
      font-weight: 500;
      line-height: 26px;
    }
  }

  .hero-card__summary {
    margin-top: 8px;
    color: #646a73;
    font-size: 14px;
    line-height: 22px;
    max-width: 720px;
  }

  .hero-card__stats {
    margin-top: 20px;
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 12px;
  }
}

.hero-stat {
  padding: 14px 16px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #edf0f2;
  display: flex;
  flex-direction: column;
  gap: 6px;

  .hero-stat__label {
    color: #646a73;
    font-size: 12px;
    line-height: 20px;
  }

  .hero-stat__value {
    color: #1f2329;
    font-size: 16px;
    font-weight: 500;
    line-height: 24px;
  }
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  line-height: 20px;

  &.is-ready {
    background: #34c72433;
    color: #2ca91f;
  }

  &.is-degraded {
    background: #f54a4533;
    color: #d03f3b;
  }
}

.warn-template {
  display: flex;
  align-items: flex-start;
  background: #fff6e5;
  border: 1px solid #ffe7ba;
  border-radius: 12px;
  padding: 14px 16px;

  .icon-span {
    width: 16px;
    height: 16px;
    margin-right: 8px;
    display: flex;
    align-items: center;
    margin-top: 4px;

    .svg-icon {
      width: 16px;
      height: 16px;
    }
  }

  .warn-template-content {
    color: #1f2329;
    font-size: 14px;
    line-height: 22px;
  }

  .warn-template-content__title {
    font-weight: 500;
  }
}

.issue-list {
  margin: 8px 0 0 18px;
}

.card-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
}

.content-card {
  padding: 20px 24px;

  .content-card__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;

    h3 {
      color: #1f2329;
      font-size: 16px;
      font-weight: 500;
      line-height: 24px;
    }
  }
}

.content-card--full {
  min-height: 320px;
}

.detail-list {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.detail-list--compact {
  margin-bottom: 20px;
}

.detail-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.detail-row__label {
  width: 132px;
  flex-shrink: 0;
  color: #646a73;
  font-size: 14px;
  line-height: 22px;
}

.detail-row__value {
  flex: 1;
  min-width: 0;
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 8px;
  color: #1f2329;
  font-size: 14px;
  line-height: 22px;
  word-break: break-all;
  text-align: right;
}

.tag-section {
  margin-top: 16px;

  .tag-section__label {
    display: inline-flex;
    margin-bottom: 10px;
    color: #646a73;
    font-size: 14px;
    line-height: 22px;
  }
}

.tag-section--last {
  margin-top: 20px;
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.config-intro {
  margin-top: 20px;
}

.config-intro__title {
  color: #1f2329;
  font-size: 14px;
  font-weight: 500;
  line-height: 22px;
}

.config-intro__description {
  margin-top: 4px;
  color: #646a73;
  font-size: 14px;
  line-height: 22px;
}

.config-block {
  margin-top: 16px;
  padding: 16px;
  border-radius: 12px;
  background: #1f2329;
  color: #ffffff;
  font-size: 13px;
  line-height: 22px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.blocked-state {
  margin-top: 24px;
  min-height: 220px;
  border: 1px dashed #d9dcdf;
  border-radius: 12px;
  background: #fafbfc;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 24px;
  text-align: left;

  .blocked-state__icon {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: #fff6e5;
    display: inline-flex;
    align-items: center;
    justify-content: center;

    .svg-icon {
      width: 16px;
      height: 16px;
    }
  }

  .blocked-state__title {
    color: #1f2329;
    font-size: 16px;
    font-weight: 500;
    line-height: 24px;
  }

  .blocked-state__description {
    margin-top: 4px;
    max-width: 520px;
    color: #646a73;
    font-size: 14px;
    line-height: 22px;
  }
}

@media (max-width: 1080px) {
  .card-grid {
    grid-template-columns: 1fr;
  }

  .hero-card .hero-card__stats {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .content-card,
  .hero-card {
    padding: 16px;
  }

  .detail-row {
    flex-direction: column;
    gap: 6px;
  }

  .detail-row__label {
    width: auto;
  }

  .detail-row__value {
    justify-content: flex-start;
    text-align: left;
  }

  .blocked-state {
    align-items: flex-start;
    justify-content: flex-start;
  }
}
</style>
