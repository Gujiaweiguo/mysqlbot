import { useCache } from '@/utils/useCache'
import { useAppearanceStoreWithOut } from '@/stores/appearance'
import { useUserStore } from '@/stores/user'
import type { Router } from 'vue-router'
import { generateDynamicRouters } from './dynamic'
import { toLoginPage } from '@/utils/utils'
import { generateLicenseRouters, initLicenseGenerator } from '@/xpack-compat'

const appearanceStore = useAppearanceStoreWithOut()
const userStore = useUserStore()
const { wsCache } = useCache()
const whiteList = ['/login', '/admin-login']
const assistantWhiteList = ['/assistant', '/assistant/index', '/embeddedPage', '/embeddedCommon', '/401']

const wsAdminRouterList = ['/ds/index', '/as/index']
export const watchRouter = (router: Router) => {
  router.beforeEach(async (to: any) => {
    await initLicenseGenerator(import.meta.env.VITE_API_BASE_URL)
    await appearanceStore.setAppearance()
    generateLicenseRouters(router)
    if ((to.path === '/login' || to.path === '/admin-login') && userStore.getUid) {
      return to?.query?.redirect || '/chat/index'
    }
    if (assistantWhiteList.includes(to.path)) {
      return true
    }
    const token = wsCache.get('user.token')
    if (whiteList.includes(to.path)) {
      return true
    }
    if (!token) {
      // ElMessage.error('Please login first')
      return toLoginPage(to.fullPath)
    }
    if (!userStore.getUid) {
      await userStore.info()
      generateDynamicRouters(router)
      const isFirstDynamicPath = to?.path && ['/ds/index', '/as/index'].includes(to.path)
      if (isFirstDynamicPath) {
        if (userStore.isSpaceAdmin) {
          return { ...to, replace: true }
        }
      }
    }
    if (to.path === '/docs') {
      location.href = to.fullPath
      return false
    }
    if (to.path === '/' || accessCrossPermission(to)) {
      return '/chat/index'
    }
    if (to.path === '/login' || to.path === '/admin-login') {
      return '/chat/index'
    }
    return true
  })
}

const accessCrossPermission = (to: any) => {
  if (!to?.path) return false
  return (
    (to.path.startsWith('/system') && !userStore.isAdmin) ||
    (to.path.startsWith('/set') && !userStore.isSpaceAdmin) ||
    (isWsAdminRouter(to) && !userStore.isSpaceAdmin)
  )
}

const isWsAdminRouter = (to?: any) => {
  return wsAdminRouterList.some((item: string) => to?.path?.startsWith(item))
}
