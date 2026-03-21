<template>
  <div
    v-if="showLoading"
    class="xpack-login-handler-mask"
    :data-stage="loadingStage"
    data-testid="login-wait-state"
  >
    <div class="login-wait-panel">
      <el-icon class="login-wait-icon is-loading" size="28">
        <Loading />
      </el-icon>
      <div class="login-wait-title" data-testid="login-wait-title">{{ loadingTitle }}</div>
      <div class="login-wait-description" data-testid="login-wait-description">
        {{ loadingDescription }}
      </div>
    </div>
  </div>

  <div class="login-container" :class="{ 'hide-login-container': showLoading }">
    <div class="login-left">
      <img :src="bg" alt="" />
    </div>
    <div class="login-content">
      <div class="login-right">
        <div class="login-logo-icon">
          <img v-if="loginBg" height="52" :src="loginBg" alt="" />
          <el-icon v-else size="52"
            ><custom_small v-if="appearanceStore.themeColor !== 'default'"></custom_small>
            <LOGO_fold v-else></LOGO_fold
          ></el-icon>
          <span style="margin-left: 14px; font-size: 34px; font-weight: 900; color: #485559">{{
            appearanceStore.name
          }}</span>
        </div>
        <div v-if="appearanceStore.getShowSlogan" class="welcome">
          {{ appearanceStore.slogan ?? $t('common.intelligent_questioning_platform') }}
        </div>
        <div v-else class="welcome" style="height: 0"></div>
        <div class="login-form">
          <div class="default-login-tabs">
            <h2 class="title">{{ $t('common.login') }}</h2>
            <el-form
              ref="loginFormRef"
              class="form-content_error"
              :model="loginForm"
              :rules="rules"
              @keyup.enter="submitForm"
            >
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  clearable
                  :disabled="isSubmitting || showLoading"
                  :placeholder="$t('common.your_account_email_address')"
                  size="large"
                ></el-input>
              </el-form-item>
              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  :disabled="isSubmitting || showLoading"
                  :placeholder="$t('common.enter_your_password')"
                  type="password"
                  show-password
                  clearable
                  size="large"
                ></el-input>
              </el-form-item>
              <el-form-item>
                <el-button
                  type="primary"
                  class="login-btn"
                  :loading="isSubmitting"
                  :disabled="isSubmitting || showLoading"
                  data-testid="account-login-submit"
                  @click="submitForm"
                  >{{
                  $t('common.login_')
                }}</el-button
                >
              </el-form-item>
            </el-form>
          </div>
          <Handler
            v-model:loading="isBootstrapping"
            jsname="L2NvbXBvbmVudC9sb2dpbi9IYW5kbGVy"
            @authenticated="startEnteringSystem"
            @switch-tab="switchTab"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script lang="ts" setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import custom_small from '@/assets/svg/logo-custom_small.svg'
import LOGO_fold from '@/assets/LOGO-fold.svg'
import login_image from '@/assets/embedded/login_image.png'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import loginImage from '@/assets/blue/login-image_blue.png'
import Handler from './xpack/Handler.vue'
import { toLoginSuccess } from '@/utils/utils'

const isBootstrapping = ref(true)
const isSubmitting = ref(false)
const isEnteringSystem = ref(false)
const router = useRouter()
const userStore = useUserStore()
const appearanceStore = useAppearanceStoreWithOut()
const { t } = useI18n()
const loginForm = ref({
  username: '',
  password: '',
})
const activeName = ref('simple')

// const isLdap = computed(() => activeName.value == 'ldap')
const bg = computed(() => {
  return appearanceStore.getBg || (appearanceStore.isBlue ? loginImage : login_image)
})

const showLoading = computed(() => isBootstrapping.value || isEnteringSystem.value)
const loadingStage = computed(() => (isEnteringSystem.value ? 'entering' : 'bootstrap'))
const loadingTitle = computed(() =>
  isEnteringSystem.value ? t('login.entering_system') : t('login.preparing_login')
)
const loadingDescription = computed(() =>
  isEnteringSystem.value ? t('login.entering_system_hint') : t('login.preparing_login_hint')
)

const loginBg = computed(() => {
  return appearanceStore.getLogin
})

const rules = {
  username: [{ required: true, message: t('common.your_account_email_address'), trigger: 'blur' }],
  password: [{ required: true, message: t('common.the_correct_password'), trigger: 'blur' }],
}

const loginFormRef = ref()

const validateLoginForm = () => {
  return new Promise<boolean>((resolve) => {
    if (!loginFormRef.value) {
      resolve(false)
      return
    }
    loginFormRef.value.validate((valid: boolean) => {
      resolve(valid)
    })
  })
}

const startEnteringSystem = () => {
  isBootstrapping.value = false
  isEnteringSystem.value = true
}

const submitForm = async () => {
  if (isSubmitting.value || showLoading.value) {
    return
  }

  const valid = await validateLoginForm()
  if (!valid) {
    return
  }

  isSubmitting.value = true
  try {
    await userStore.login(loginForm.value)
  } catch {
    isSubmitting.value = false
    return
  }

  isSubmitting.value = false
  startEnteringSystem()
  await toLoginSuccess(router)
}

const switchTab = (name: string) => {
  activeName.value = name || 'simple'
}
</script>

<style lang="less" scoped>
.login-container {
  height: 100vh;
  width: 100vw;
  background-color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;

  .login-left {
    display: flex;
    height: 100%;
    width: 40%;
    img {
      height: 100%;
      max-width: 100%;
    }
  }

  .login-content {
    display: flex;
    align-items: center;
    justify-content: center;
    flex: 1;

    .login-right {
      display: flex;
      align-items: center;
      flex-direction: column;
      position: relative;

      .login-logo-icon {
        width: auto;
        height: 52px;
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .welcome {
        margin: 8px 0 40px 0;
        font-weight: 400;
        font-size: 14px;
        line-height: 20px;
        color: #646a73;
      }

      .login-form {
        border: 1px solid #dee0e3;
        padding: 40px;
        width: 480px;
        min-height: 392px;
        border-radius: 12px;
        box-shadow: 0px 6px 24px 0px #1f232914;

        .form-content_error {
          .ed-form-item--default {
            margin-bottom: 24px;
            &.is-error {
              margin-bottom: 48px;
            }
          }
        }

        .title {
          font-weight: 500;
          font-style: Medium;
          font-size: 20px;
          line-height: 28px;
          margin-bottom: 24px;
        }

        .login-btn {
          width: 100%;
          height: 40px;
          font-size: 16px;
          border-radius: 4px;
        }

        .agreement {
          margin-top: 20px;
          text-align: center;
          color: #666;
        }
      }
    }
  }
}
.hide-login-container {
  display: none;
}
:deep(.ed-input__wrapper) {
  background-color: #f5f7fa;
}
.xpack-login-handler-mask {
  position: fixed;
  inset: 0;
  z-index: 999;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-color);

  .login-wait-panel {
    width: min(420px, calc(100vw - 48px));
    padding: 32px;
    border: 1px solid var(--border-color);
    border-radius: 12px;
    background: var(--white);
    box-shadow: var(--shadow);
    display: flex;
    flex-direction: column;
    align-items: center;
    row-gap: 12px;
    text-align: center;
  }

  .login-wait-icon {
    color: var(--primary-color);
  }

  .login-wait-title {
    color: var(--text-color);
    font-size: 18px;
    font-weight: 600;
    line-height: 28px;
  }

  .login-wait-description {
    color: var(--text-light);
    font-size: 14px;
    line-height: 20px;
  }
}
</style>
