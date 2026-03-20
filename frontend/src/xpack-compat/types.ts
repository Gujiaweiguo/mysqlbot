import type { Router } from 'vue-router'

export type LicenseStatus = {
  status?: string
  [key: string]: unknown
}

export interface LicenseGeneratorContract {
  init: (baseUrl: string) => Promise<boolean | void>
  getLicense: () => LicenseStatus
  generateRouters: (router: Router) => void
  sqlbotEncrypt: (value: string) => string
  generate?: () => string
}
