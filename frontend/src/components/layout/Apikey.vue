<script lang="ts" setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import SuccessFilled from '@/assets/svg/gou_icon.svg'
import CircleCloseFilled from '@/assets/svg/icon_ban_filled.svg'
import icon_warning_filled from '@/assets/svg/icon_info_colorful.svg'
import icon_add_outlined from '@/assets/svg/icon_add_outlined.svg'
import icon_visible_outlined_blod from '@/assets/embedded/icon_visible_outlined_blod.svg'
import icon_copy_outlined from '@/assets/svg/icon_copy_outlined.svg'
import IconOpeDelete from '@/assets/svg/icon_delete.svg'
import icon_invisible_outlined from '@/assets/embedded/icon_invisible_outlined.svg'
import icon_visible_outlined from '@/assets/embedded/icon_visible_outlined.svg'
import { formatTimestamp } from '@/utils/date'
import { useClipboard } from '@vueuse/core'
import EmptyBackground from '@/views/dashboard/common/EmptyBackground.vue'
import { request } from '@/utils/request'
import { buildOpenClawAuthHeaderValue, generateOpenClawToken } from '@/utils/openclawToken'

interface ApiKeyRow {
  id: number
  access_key: string
  secret_key: string
  status: boolean
  create_time: number
  showPwd?: boolean
  openclawToken?: string
  showOpenclawToken?: boolean
}

type CopyVariant = 'raw' | 'header'

const { t } = useI18n()

const limitCount = ref(5)
const limitValid = ref(true)

const triggerLimit = computed(() => {
  return limitValid.value && state.tableData.length >= limitCount.value
})
const state = reactive({
  tableData: [] as ApiKeyRow[],
})

const handleAdd = () => {
  if (triggerLimit.value) {
    return
  }
  request.post('/system/apikey', {}).then(() => {
    loadGridData()
  })
}
const pwd = ref('**********')
const tokenMask = ref('••••••••••••••••••••••••')

const hydrateRow = (row: ApiKeyRow): ApiKeyRow => {
  return {
    ...row,
    showPwd: false,
    openclawToken: '',
    showOpenclawToken: false,
  }
}

const toApiDoc = () => {
  console.log('Add API Key')
  const url = '/docs'
  window.open(url, '_blank')
}

const statusHandler = (row: any) => {
  const param = {
    id: row.id,
    status: row.status,
  }
  request.put('/system/apikey/status', param).then(() => {
    loadGridData()
  })
}
const { copy } = useClipboard({ legacy: true })

const copyCode = (row: ApiKeyRow, key: 'access_key' | 'secret_key' = 'secret_key') => {
  copy(row[key])
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}
const buildTokenValue = (row: ApiKeyRow) => {
  row.openclawToken = generateOpenClawToken({
    accessKey: row.access_key,
    secretKey: row.secret_key,
  })
  row.showOpenclawToken = false
}

const ensureTokenValue = (row: ApiKeyRow): string => {
  if (!row.openclawToken) {
    buildTokenValue(row)
  }

  return row.openclawToken || ''
}

const getTokenPreview = (row: ApiKeyRow): string => {
  if (!row.openclawToken) {
    return t('api_key.token_not_generated')
  }

  return row.showOpenclawToken ? row.openclawToken : tokenMask.value
}

const copyGeneratedToken = (row: ApiKeyRow, variant: CopyVariant) => {
  const token = ensureTokenValue(row)
  const value = variant === 'raw' ? token : buildOpenClawAuthHeaderValue(token)

  copy(value)
    .then(function () {
      ElMessage.success(t('embedded.copy_successful'))
    })
    .catch(function () {
      ElMessage.error(t('embedded.copy_failed'))
    })
}

const deleteHandler = (row: ApiKeyRow) => {
  ElMessageBox.confirm(t('user.del_key', { msg: row.access_key }), {
    confirmButtonType: 'danger',
    confirmButtonText: t('dashboard.delete'),
    cancelButtonText: t('common.cancel'),
    customClass: 'confirm-no_icon',
    autofocus: false,
    callback: (action: any) => {
      if (action === 'confirm') {
        request.delete(`/system/apikey/${row.id}`).then(() => {
          loadGridData()
          ElMessage({
            type: 'success',
            message: t('dashboard.delete_success'),
          })
        })
      }
    },
  })
}
const sortChange = (param: any) => {
  if (param?.order === 'ascending') {
    state.tableData.sort((a, b) => a.create_time - b.create_time)
  } else {
    state.tableData.sort((a, b) => b.create_time - a.create_time)
  }
}
const loadGridData = () => {
  request.get('/system/apikey').then((res: ApiKeyRow[]) => {
    state.tableData = (res || []).map(hydrateRow)
  })
}
onMounted(() => {
  loadGridData()
})
</script>

<template>
  <div class="sqlbot-apikey-container">
    <div class="warn-template">
      <span class="icon-span">
        <el-icon>
          <Icon name="icon_warning_filled"><icon_warning_filled class="svg-icon" /></Icon>
        </el-icon>
      </span>
      <div class="warn-template-content">
        <span>{{ t('api_key.info_tips') }}</span>
      </div>
    </div>

    <div class="token-guide">
      <p class="token-guide__title">{{ t('api_key.openclaw_guide_title') }}</p>
      <p class="token-guide__text">{{ t('api_key.orchestrator_agent_hint') }}</p>
      <p class="token-guide__text">{{ t('api_key.header_token_hint') }}</p>
      <p class="token-guide__text token-guide__text--warning">
        {{ t('api_key.generated_token_warning') }}
      </p>
      <p class="token-guide__caption">{{ t('api_key.ephemeral_token_hint') }}</p>
    </div>

    <div class="api-key-btn">
      <el-tooltip
        v-if="triggerLimit"
        :offset="14"
        effect="dark"
        :content="t('api_key.trigger_limit', [limitCount])"
        placement="top"
      >
        <el-button v-if="triggerLimit" type="info" disabled>
          <template #icon>
            <icon_add_outlined></icon_add_outlined>
          </template>
          {{ $t('api_key.create') }}
        </el-button>
      </el-tooltip>
      <el-button v-else type="primary" @click="handleAdd">
        <template #icon>
          <icon_add_outlined></icon_add_outlined>
        </template>
        {{ $t('api_key.create') }}
      </el-button>

      <el-button secondary @click="toApiDoc">
        <template #icon>
          <icon_visible_outlined_blod></icon_visible_outlined_blod>
        </template>
        {{ $t('api_key.to_doc') }}
      </el-button>
    </div>
    <div class="api-key-grid">
      <el-table
        ref="multipleTableRef"
        :data="state.tableData"
        style="width: 100%"
        @sort-change="sortChange"
      >
        <el-table-column prop="access_key" label="Access Key" width="206">
          <template #default="scope">
            <div class="user-status-container">
              <div :title="scope.row.access_key" class="ellipsis" style="max-width: 208px">
                {{ scope.row.access_key }}
              </div>
              <el-tooltip
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon
                  size="16"
                  class="hover-icon_with_bg"
                  @click="copyCode(scope.row, 'access_key')"
                >
                  <icon_copy_outlined></icon_copy_outlined>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="secret_key" label="Secret Key" width="206">
          <template #default="scope">
            <div class="user-status-container">
              <div
                :title="scope.row.showPwd ? scope.row.secret_key : pwd"
                class="ellipsis"
                style="max-width: 208px"
              >
                {{ scope.row.showPwd ? scope.row.secret_key : pwd }}
              </div>
              <el-tooltip
                :offset="12"
                effect="dark"
                :content="t('datasource.copy')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="copyCode(scope.row)">
                  <icon_copy_outlined></icon_copy_outlined>
                </el-icon>
              </el-tooltip>

              <el-tooltip
                v-if="scope.row.showPwd"
                :offset="12"
                effect="dark"
                :content="t('embedded.click_to_hide')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = false">
                  <icon_visible_outlined></icon_visible_outlined>
                </el-icon>
              </el-tooltip>

              <el-tooltip
                v-if="!scope.row.showPwd"
                :offset="12"
                effect="dark"
                :content="t('embedded.click_to_show')"
                placement="top"
              >
                <el-icon class="hover-icon_with_bg" size="16" @click="scope.row.showPwd = true">
                  <icon_invisible_outlined></icon_invisible_outlined>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="openclaw_token" :label="t('api_key.openclaw_token')" min-width="320">
          <template #default="scope">
            <div class="token-cell">
              <div class="token-cell__value">
                <div :title="getTokenPreview(scope.row)" class="ellipsis token-cell__value-text">
                  {{ getTokenPreview(scope.row) }}
                </div>

                <el-tooltip
                  v-if="scope.row.openclawToken && scope.row.showOpenclawToken"
                  :offset="12"
                  effect="dark"
                  :content="t('embedded.click_to_hide')"
                  placement="top"
                >
                  <el-icon
                    class="hover-icon_with_bg"
                    size="16"
                    @click="scope.row.showOpenclawToken = false"
                  >
                    <icon_visible_outlined></icon_visible_outlined>
                  </el-icon>
                </el-tooltip>

                <el-tooltip
                  v-else-if="scope.row.openclawToken"
                  :offset="12"
                  effect="dark"
                  :content="t('embedded.click_to_show')"
                  placement="top"
                >
                  <el-icon
                    class="hover-icon_with_bg"
                    size="16"
                    @click="scope.row.showOpenclawToken = true"
                  >
                    <icon_invisible_outlined></icon_invisible_outlined>
                  </el-icon>
                </el-tooltip>
              </div>

              <div class="token-cell__actions">
                <el-button text type="primary" @click="buildTokenValue(scope.row)">
                  {{
                    t(`api_key.${scope.row.openclawToken ? 'regenerate_token' : 'generate_token'}`)
                  }}
                </el-button>
                <el-button
                  text
                  :disabled="!scope.row.openclawToken"
                  @click="copyGeneratedToken(scope.row, 'raw')"
                >
                  {{ t('api_key.copy_jwt') }}
                </el-button>
                <el-button
                  text
                  :disabled="!scope.row.openclawToken"
                  @click="copyGeneratedToken(scope.row, 'header')"
                >
                  {{ t('api_key.copy_sk_token') }}
                </el-button>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="status" width="100" :label="t('datasource.enabled_status')">
          <template #default="scope">
            <div class="api-status-container" :class="[scope.row.status ? 'active' : 'disabled']">
              <el-icon size="16">
                <SuccessFilled v-if="scope.row.status" />
                <CircleCloseFilled v-else />
              </el-icon>
              <span>{{ $t(`user.${scope.row.status ? 'enabled' : 'disabled'}`) }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="create_time" width="180" sortable :label="t('user.creation_time')">
          <template #default="scope">
            <span>{{ formatTimestamp(scope.row.create_time, 'YYYY-MM-DD HH:mm:ss') }}</span>
          </template>
        </el-table-column>
        <el-table-column fixed="right" width="100" :label="$t('ds.actions')">
          <template #default="scope">
            <div class="table-operate">
              <el-switch
                v-model="scope.row.status"
                :active-value="true"
                :inactive-value="false"
                size="small"
                @change="statusHandler(scope.row)"
              />
              <div class="line"></div>
              <el-tooltip
                :offset="14"
                effect="dark"
                :content="$t('dashboard.delete')"
                placement="top"
              >
                <el-icon class="action-btn" size="16" @click="deleteHandler(scope.row)">
                  <IconOpeDelete></IconOpeDelete>
                </el-icon>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <EmptyBackground
            v-if="!state.tableData.length"
            :description="$t('datasource.relevant_content_found')"
            img-type="none"
          />
        </template>
      </el-table>
    </div>
  </div>
</template>

<style lang="less" scoped>
.sqlbot-apikey-container {
  background: #ffffff;
  border-radius: 8px;
  row-gap: 24px;
  display: flex;
  flex-direction: column;

  .warn-template {
    display: flex;
    align-items: center;
    background: #d2f1e9;
    // border: 1px solid #ffe7ba;
    border-radius: 6px;
    padding: 9px 16px;

    .icon-span {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      display: flex;
      align-items: center;
      margin-top: -20px;
      i {
        width: 16px;
        height: 16px;
      }

      .svg-icon {
        width: 16px;
        height: 16px;
      }
    }

    .warn-template-content {
      font-size: 14px;
      color: #1f2329;
    }
  }

  .api-key-btn {
    margin-bottom: 0px;

    .el-button {
      margin-right: 8px;
    }
  }

  .token-guide {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: 14px 16px;
    border: 1px solid #dee0e3;
    border-radius: 8px;
    background: #fafbfc;

    .token-guide__title {
      color: #1f2329;
      font-size: 14px;
      font-weight: 500;
      line-height: 22px;
    }

    .token-guide__text {
      color: #1f2329;
      font-size: 14px;
      line-height: 22px;
    }

    .token-guide__text--warning {
      color: #b54708;
    }

    .token-guide__caption {
      color: #646a73;
      font-size: 12px;
      line-height: 20px;
    }
  }

  .api-key-grid {
    width: 100%;
    .el-table {
      width: 100%;
    }

    .table-operate {
      display: flex;
      align-items: center;

      .line {
        width: 1px;
        height: 16px;
        background: #e8e8e8;
        margin: 0 12px;
      }

      .action-btn {
        width: 24px;
        height: 24px;
        border-radius: 6px;
        cursor: pointer;
        color: #646a73;

        &:hover {
          background-color: #1f23291a;
        }
      }
    }
    .api-status-container {
      display: flex;
      align-items: center;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;

      .ed-icon {
        margin-right: 8px;
      }
    }
    .user-status-container {
      display: flex;
      align-items: center;
      font-weight: 400;
      font-size: 14px;
      line-height: 22px;
      height: 24px;

      .ed-icon {
        margin-left: 8px;
      }

      .ed-icon + .ed-icon {
        margin-left: 12px;
      }
    }

    .token-cell {
      display: flex;
      flex-direction: column;
      gap: 6px;
      padding: 6px 0;
    }

    .token-cell__value {
      display: flex;
      align-items: center;
      gap: 8px;
      min-width: 0;
    }

    .token-cell__value-text {
      color: #1f2329;
      max-width: 100%;
    }

    .token-cell__actions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;

      .el-button {
        margin-left: 0;
        padding: 0;
        height: 22px;
      }
    }
  }
}
</style>
