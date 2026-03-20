import { expect, test } from '@playwright/test'

import { installLicenseGeneratorContractMocks } from './fixtures/chat-fixtures'

type LicenseContractState = {
  encryptedValues: Array<{ input: string; output: string }>
  generateRoutersCalls: number
  getLicenseCalls: number
  initArgs: string[]
}

type LicenseGeneratorContract = {
  generateRouters: () => undefined
  getLicense: () => { status: string }
  init: (baseUrl: string) => Promise<boolean>
  sqlbotEncrypt: (value: string) => string
}

test.describe('LicenseGenerator contract characterization', () => {
  test.beforeEach(async ({ page }) => {
    await installLicenseGeneratorContractMocks(page)
  })

  test('initializes router bootstrap contract from the local facade', async ({ page }) => {
    await page.goto('/#/login')

    await expect
      .poll(async () => {
        return page.evaluate(() => {
          return (
            window as Window & {
              __licenseContract?: LicenseContractState
            }
          ).__licenseContract?.generateRoutersCalls
        })
      })
      .toBe(1)

    const state = await page.evaluate(() => {
      return (window as Window & { __licenseContract: LicenseContractState }).__licenseContract
    })

    expect(state.initArgs).toHaveLength(1)
    expect(state.initArgs[0]).toContain('/api/v1')
    expect(state.generateRoutersCalls).toBe(1)
  })

  test('exposes stable global contract methods for current frontend callers', async ({ page }) => {
    await page.goto('/#/login')

    const contractShape = await page.evaluate(() => {
      const context = window as Window & {
        LicenseGenerator: LicenseGeneratorContract
      }

      return {
        encryptResult: context.LicenseGenerator.sqlbotEncrypt('demo'),
        hasGenerateRouters: typeof context.LicenseGenerator.generateRouters,
        hasGetLicense: typeof context.LicenseGenerator.getLicense,
        hasInit: typeof context.LicenseGenerator.init,
        licenseStatus: context.LicenseGenerator.getLicense().status,
      }
    })

    expect(contractShape.hasInit).toBe('function')
    expect(contractShape.hasGetLicense).toBe('function')
    expect(contractShape.hasGenerateRouters).toBe('function')
    expect(contractShape.encryptResult).toBe('enc::demo')
    expect(contractShape.licenseStatus).toBe('invalid')
  })
})
