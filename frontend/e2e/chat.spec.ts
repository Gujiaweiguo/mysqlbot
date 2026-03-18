import { expect, test } from '@playwright/test'

import {
  installChatErrorFlowMocks,
  installChatFlowMocks,
  installChatReplayFlowMocks,
  seedAuthenticatedUser,
} from './fixtures/chat-fixtures'

test.describe('chat Playwright baseline', () => {
  test.beforeEach(async ({ page }) => {
    await installChatFlowMocks(page)
    await seedAuthenticatedUser(page)
  })

  test('creates a new chat and renders streamed answer state', async ({ page }) => {
    await page.goto('/#/chat/index')

    await expect(page.getByTestId('chat-welcome')).toBeVisible()
    await page.getByTestId('new-chat-button').click()
    const datasourceDrawer = page.locator('[data-testid="datasource-drawer"]:visible')
    await expect(datasourceDrawer).toBeVisible()

    await datasourceDrawer.getByTestId('datasource-card-101').click()
    await datasourceDrawer.getByTestId('confirm-datasource-button').click()

    await page.getByTestId('chat-input').fill('Show revenue by month')
    await page.getByTestId('send-button').click()

    await expect(page.getByTestId('thinking-indicator')).toBeVisible()
    await expect(page.getByTestId('user-message').last()).toContainText('Show revenue by month')
    await expect(page.getByTestId('chart-block').last()).toBeVisible()
    await expect(page.getByTestId('recommended-question-chat-0')).toContainText(
      'Show top customers'
    )
  })

  test('loads historical chat conversation from sidebar', async ({ page }) => {
    await page.goto('/#/chat/index')

    await page.getByTestId('chat-item-9002').click()

    await expect(page.getByTestId('chat-scroll')).toContainText('Show revenue by month')
    await expect(page.getByTestId('chart-block').first()).toBeVisible()
    await expect(page.getByTestId('chat-input')).toBeEnabled()
  })
})

test.describe('chat error paths', () => {
  test.beforeEach(async ({ page }) => {
    await installChatErrorFlowMocks(page)
    await seedAuthenticatedUser(page)
  })

  test('renders streamed error state after question submission failure', async ({ page }) => {
    await page.goto('/#/chat/index')

    await expect(page.getByTestId('chat-welcome')).toBeVisible()
    await page.getByTestId('new-chat-button').click()
    const datasourceDrawer = page.locator('[data-testid="datasource-drawer"]:visible')
    await expect(datasourceDrawer).toBeVisible()

    await datasourceDrawer.getByTestId('datasource-card-101').click()
    await datasourceDrawer.getByTestId('confirm-datasource-button').click()

    await page.getByTestId('chat-input').fill('Show revenue by month')
    await page.getByTestId('send-button').click()

    await expect(page.getByTestId('user-message').last()).toContainText('Show revenue by month')
    await expect(page.getByTestId('chat-error-container')).toBeVisible()
    await expect(page.getByTestId('chat-error-container')).toContainText('database connection')
    await expect(page.getByTestId('thinking-indicator')).toHaveCount(0)
    await expect(page.getByTestId('chat-input')).toBeEnabled()
    await expect(page.getByTestId('chart-block')).toHaveCount(0)
  })
})

test.describe('chat recommended-question replay', () => {
  test.beforeEach(async ({ page }) => {
    await installChatReplayFlowMocks(page)
    await seedAuthenticatedUser(page)
  })

  test('clicking a recommended question continues the conversation', async ({ page }) => {
    await page.goto('/#/chat/index')

    await page.getByTestId('chat-item-9002').click()

    await expect(page.getByTestId('chat-scroll')).toContainText('Show revenue by month')
    await expect(page.getByTestId('recommended-question-chat-0')).toContainText(
      'Show top customers'
    )
    await expect(page.getByTestId('chart-block')).toHaveCount(1)

    await page.getByTestId('recommended-question-chat-0').click()

    await expect(page.getByTestId('user-message').last()).toContainText('Show top customers')
    await expect(page.getByTestId('chat-scroll')).toContainText('Show monthly trends', {
      timeout: 15000,
    })
  })
})
