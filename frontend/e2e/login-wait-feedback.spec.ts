import { expect, test, type Page } from '@playwright/test'

import {
  installBaseAppMocks,
  installChatFlowMocks,
  installLicenseGeneratorMock,
} from './fixtures/chat-fixtures'

type Deferred = {
  promise: Promise<void>
  resolve: () => void
}

const loginUserInfo = {
  id: '1',
  account: 'admin',
  name: 'Admin',
  oid: 'workspace-1',
  language: 'en',
  exp: 0,
  time: 0,
  weight: 1,
  origin: 0,
}

const createDeferred = (): Deferred => {
  let resolve: () => void = () => undefined
  const promise = new Promise<void>((done) => {
    resolve = done
  })

  return {
    promise,
    resolve,
  }
}

async function seedLoginLanguage(page: Page) {
  await page.addInitScript(() => {
    localStorage.setItem(
      'user.language',
      JSON.stringify({
        c: Date.now(),
        e: Date.now() + 24 * 60 * 60 * 1000,
        v: JSON.stringify('en'),
      })
    )
  })
}

async function mockDefaultLoginBootstrap(
  page: Page,
  options?: {
    platformStatusGate?: Deferred
    loginDefault?: string
    platformStatusBody?: Array<{ name: string; enable: boolean }>
  }
) {
  await page.route('**/system/authentication/platform/status**', async (route) => {
    await options?.platformStatusGate?.promise
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(options?.platformStatusBody ?? []),
    })
  })

  await page.route('**/system/parameter/login**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          pkey: 'login.default_login',
          pval: options?.loginDefault ?? '0',
        },
      ]),
    })
  })
}

test.describe('login wait feedback', () => {
  test('shows explicit bootstrap feedback before login options are ready', async ({ page }) => {
    const platformStatusGate = createDeferred()

    await seedLoginLanguage(page)
    await installBaseAppMocks(page)
    await installLicenseGeneratorMock(page, {
      scriptBody: `var LicenseGenerator = {
        init: async function () { return true },
        getLicense: function () { return { status: 'valid' } },
        generateRouters: function () { return undefined },
        sqlbotEncrypt: function (value) { return value },
      };
      window.LicenseGenerator = LicenseGenerator;
      globalThis.LicenseGenerator = LicenseGenerator;`,
    })
    await mockDefaultLoginBootstrap(page, { platformStatusGate })

    await page.goto('/#/login')

    await expect(page.getByTestId('login-wait-state')).toBeVisible()
    await expect(page.getByTestId('login-wait-state')).toHaveAttribute('data-stage', 'bootstrap')
    await expect(page.getByTestId('login-wait-title')).toHaveText('Preparing sign-in options')
    await expect(page.getByTestId('login-wait-description')).toHaveText(
      'Checking available login methods and redirect settings.'
    )

    platformStatusGate.resolve()

    await expect(page.getByTestId('login-wait-state')).toHaveCount(0)
    await expect(page.getByTestId('account-login-submit')).toBeVisible()
  })

  test('prevents duplicate account submits and shows entering-system feedback after success', async ({
    page,
  }) => {
    let loginAttempts = 0
    const loginGate = createDeferred()
    const userInfoGate = createDeferred()

    await seedLoginLanguage(page)
    await installChatFlowMocks(page)
    await mockDefaultLoginBootstrap(page)

    await page.route('**/api/v1/login/access-token', async (route) => {
      loginAttempts += 1
      await loginGate.promise
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          access_token: 'login-token',
          exp: 1893456000,
        }),
      })
    })

    await page.route('**/api/v1/user/info', async (route) => {
      await userInfoGate.promise
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(loginUserInfo),
      })
    })

    await page.goto('/#/login')

    await page.getByPlaceholder('Please enter your account/email address').fill('admin')
    await page.getByPlaceholder('Please enter your password').fill('password')

    const submitButton = page.getByTestId('account-login-submit')
    await submitButton.click()
    await page.keyboard.press('Enter')

    await expect(submitButton).toBeDisabled()
    await expect(submitButton).toHaveClass(/is-loading/)
    await expect.poll(() => loginAttempts).toBe(1)

    loginGate.resolve()

    await expect(page.getByTestId('login-wait-state')).toBeVisible()
    await expect(page.getByTestId('login-wait-state')).toHaveAttribute('data-stage', 'entering')
    await expect(page.getByTestId('login-wait-title')).toHaveText('Entering the system')
    await expect(page.getByTestId('login-wait-description')).toHaveText(
      'Authentication succeeded. Loading your destination.'
    )

    userInfoGate.resolve()

    await expect(page).toHaveURL(/#\/chat/)
  })

  test('keeps failed account logins on the login page and re-enables submit', async ({ page }) => {
    const loginGate = createDeferred()

    await seedLoginLanguage(page)
    await installBaseAppMocks(page)
    await mockDefaultLoginBootstrap(page)

    await page.route('**/api/v1/login/access-token', async (route) => {
      await loginGate.promise
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Invalid credentials' }),
      })
    })

    await page.goto('/#/login')

    await page.getByPlaceholder('Please enter your account/email address').fill('admin')
    await page.getByPlaceholder('Please enter your password').fill('wrong-password')

    const submitButton = page.getByTestId('account-login-submit')
    await submitButton.click()

    await expect(submitButton).toBeDisabled()
    await expect(submitButton).toHaveClass(/is-loading/)

    loginGate.resolve()

    await expect(submitButton).toBeEnabled()
    await expect(page.getByTestId('login-wait-state')).toHaveCount(0)
    await expect(page).toHaveURL(/#\/login/)
  })

})
