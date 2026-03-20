import type { LicenseGeneratorContract } from './types'

declare global {
  interface Window {
    LicenseGenerator: LicenseGeneratorContract
  }

  const LicenseGenerator: LicenseGeneratorContract
}

export {}
