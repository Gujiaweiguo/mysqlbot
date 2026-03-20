import type { Router } from 'vue-router'

import type { LicenseGeneratorContract, LicenseStatus } from './types'

let initializedBaseUrl = ''

const localLicenseGenerator: LicenseGeneratorContract = {
  async init(baseUrl: string): Promise<boolean> {
    initializedBaseUrl = baseUrl
    return true
  },
  getLicense(): LicenseStatus {
    return {
      status: 'valid',
      baseUrl: initializedBaseUrl,
    }
  },
  generateRouters(_router: Router): void {},
  sqlbotEncrypt(value: string): string {
    return value
  },
  generate(): string {
    return `${Date.now()}`
  },
}

const installGlobalLicenseGenerator = (): LicenseGeneratorContract => {
  window.LicenseGenerator = localLicenseGenerator
  ;(globalThis as unknown as Window).LicenseGenerator = localLicenseGenerator
  return localLicenseGenerator
}

const getLicenseGenerator = (): LicenseGeneratorContract => {
  return window.LicenseGenerator || installGlobalLicenseGenerator()
}

if (!window.LicenseGenerator) {
  installGlobalLicenseGenerator()
}

export const licenseGenerator = {
  getInstance(): LicenseGeneratorContract {
    return getLicenseGenerator()
  },
  init(baseUrl: string): Promise<boolean | void> {
    return getLicenseGenerator().init(baseUrl)
  },
  getLicense(): LicenseStatus {
    return getLicenseGenerator().getLicense()
  },
  generateRouters(router: Router): void {
    getLicenseGenerator().generateRouters(router)
  },
  sqlbotEncrypt(value: string): string {
    return getLicenseGenerator().sqlbotEncrypt(value)
  },
  generate(): string | undefined {
    return getLicenseGenerator().generate?.()
  },
}

export const initLicenseGenerator = (baseUrl: string): Promise<boolean | void> => {
  return licenseGenerator.init(baseUrl)
}

export const getLicense = (): LicenseStatus => {
  return licenseGenerator.getLicense()
}

export const generateLicenseRouters = (router: Router): void => {
  licenseGenerator.generateRouters(router)
}

export const sqlbotEncrypt = (value: string): string => {
  return licenseGenerator.sqlbotEncrypt(value)
}
