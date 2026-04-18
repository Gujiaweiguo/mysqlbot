import { expect, test } from '@playwright/test'

import { installBaseAppMocks, seedAuthenticatedUser } from './fixtures/chat-fixtures'

const mockApiKeys = [
  {
    id: '9001',
    access_key: 'e2e-access-key-001',
    secret_key: 'e2e-secret-key-001',
    status: true,
    create_time: Date.now(),
  },
  {
    id: '9002',
    access_key: 'e2e-access-key-002',
    secret_key: 'e2e-secret-key-002',
    status: true,
    create_time: Date.now(),
  },
]

function envelope<T>(data: T) {
  return JSON.stringify({ code: 0, data, msg: null })
}

async function installApiKeyMocks(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/system/apikey', async (route) => {
    if (route.request().method() === 'GET') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: envelope(mockApiKeys),
      })
    } else {
      await route.continue()
    }
  })
}

async function openApiKeyDialog(page: import('@playwright/test').Page) {
  await page.locator('button.person').click()
  const popover = page.locator('.system-person')
  await expect(popover).toBeVisible()
  await popover.locator('.popover-item', { hasText: 'API Key' }).click()
  await expect(page.getByRole('dialog').filter({ hasText: 'API Key' })).toBeVisible()
}

test.describe('API Key OpenClaw token generation', () => {
  test.beforeEach(async ({ page }) => {
    await seedAuthenticatedUser(page)
    await installBaseAppMocks(page)
    await installApiKeyMocks(page)
    await page.goto('/#/chat/index')
    await page.waitForSelector('button.person')
  })

  test('generates token, keeps it hidden by default, reveals on click', async ({ page }) => {
    await openApiKeyDialog(page)

    const table = page.locator('.sqlbot-apikey-container .ed-table__body')
    await expect(table).toBeVisible({ timeout: 10000 })

    const rows = table.locator('tbody tr')
    await expect(rows).toHaveCount(2, { timeout: 10000 })

    const firstRow = rows.first()
    const tokenCell = firstRow.locator('.token-cell')
    await expect(tokenCell.getByText('按需生成')).toBeVisible()

    await tokenCell.getByText('生成令牌').click()

    await expect(tokenCell.locator('.token-cell__value-text')).toContainText(
      '••••••••••••••••••••••••'
    )

    const revealIcons = tokenCell.locator('.token-cell__value .hover-icon_with_bg')
    await revealIcons.last().click()

    const revealedText = await tokenCell.locator('.token-cell__value-text').innerText()
    expect(revealedText).toMatch(/^eyJ[A-Za-z0-9_-]+\./)

    await expect(tokenCell.getByText('复制 JWT')).toBeEnabled()
    await expect(tokenCell.getByText('复制 sk <jwt>')).toBeEnabled()
    await expect(tokenCell.getByText('重新生成')).toBeVisible()

    const guide = page.locator('.sqlbot-apikey-container .token-guide')
    await expect(guide).toContainText('OrchestratorAgent')
    await expect(guide).toContainText('X-SQLBOT-ASK-TOKEN')
    await expect(guide).toContainText('敏感')
  })

  test('regenerates token when clicking regenerate', async ({ page }) => {
    await openApiKeyDialog(page)

    const rows = page.locator('.sqlbot-apikey-container .ed-table__body tbody tr')
    await expect(rows).toHaveCount(2, { timeout: 10000 })

    const firstRow = rows.first()
    const tokenCell = firstRow.locator('.token-cell')

    await tokenCell.getByText('生成令牌').click()

    const revealIcons = tokenCell.locator('.token-cell__value .hover-icon_with_bg')
    await revealIcons.last().click()
    const firstToken = await tokenCell.locator('.token-cell__value-text').innerText()

    await tokenCell.getByText('重新生成').click()

    const revealIcons2 = tokenCell.locator('.token-cell__value .hover-icon_with_bg')
    await revealIcons2.last().click()
    const secondToken = await tokenCell.locator('.token-cell__value-text').innerText()

    expect(secondToken).toMatch(/^eyJ[A-Za-z0-9_-]+\./)
    expect(secondToken).toBe(firstToken)
  })

  test('each row maintains independent token state', async ({ page }) => {
    await openApiKeyDialog(page)

    const rows = page.locator('.sqlbot-apikey-container .ed-table__body tbody tr')
    await expect(rows).toHaveCount(2, { timeout: 10000 })

    const firstTokenCell = rows.nth(0).locator('.token-cell')
    const secondTokenCell = rows.nth(1).locator('.token-cell')

    await expect(firstTokenCell.getByText('按需生成')).toBeVisible()
    await expect(secondTokenCell.getByText('按需生成')).toBeVisible()

    await firstTokenCell.getByText('生成令牌').click()

    await expect(firstTokenCell.locator('.token-cell__value-text')).toContainText(
      '••••••••••••••••••••••••'
    )
    await expect(secondTokenCell.getByText('按需生成')).toBeVisible()
  })
})
