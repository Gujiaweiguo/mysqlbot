<template>
  <div class="default-login-tabs-ldap">
    <h2 class="title">{{ t('login.ldap_login') }}</h2>
    <el-form
      ref="loginFormRef"
      class="form-content_error"
      :model="loginForm"
      @keyup.enter="submitForm"
    >
      <el-form-item prop="username">
        <el-input
          v-model="loginForm.username"
          clearable
          :disabled="isSubmitting"
          :placeholder="t('login.input_account')"
          size="large"
        ></el-input>
      </el-form-item>
      <el-form-item prop="password">
        <el-input
          v-model="loginForm.password"
          :disabled="isSubmitting"
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
          :disabled="isSubmitting"
          data-testid="ldap-login-submit"
          @click="submitForm"
          >{{
          $t('common.login_')
        }}</el-button
        >
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { request } from '@/utils/request'
import { useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user.ts'

const userStore = useUserStore()
const router = useRouter()
const { t } = useI18n()
const emits = defineEmits(['authenticated'])
const isSubmitting = ref(false)
const loginForm = ref({
  username: '',
  password: '',
  origin: 1,
})
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
const submitForm = async () => {
  if (isSubmitting.value) {
    return
  }

  const valid = await validateLoginForm()
  if (!valid) {
    return
  }

  isSubmitting.value = true
  try {
    const data = { ...loginForm.value }
    const res: any = await request.post('/system/authentication/sso/3', data)
    const token = res.access_token
    userStore.setToken(token)
    userStore.setExp(res.exp)
    userStore.setTime(Date.now())
    userStore.setPlatformInfo({
      flag: 'ldap',
      data: null,
      origin: 3,
    })
    emits('authenticated')
    await router.push('/')
  } catch {
    isSubmitting.value = false
  }
}
</script>

<style lang="less" scoped>
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
</style>
