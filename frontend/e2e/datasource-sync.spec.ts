import { expect, test, type Page } from '@playwright/test'
import CryptoJS from 'crypto-js'

import { installBaseAppMocks } from './fixtures/chat-fixtures'

const encryptionKey = CryptoJS.enc.Utf8.parse('SQLBot1234567890')

const encryptedConfiguration = CryptoJS.AES.encrypt(
  JSON.stringify({
    host: '127.0.0.1',
    port: 5432,
    username: 'sqlbot',
    password: 'Password123',
    database: 'sqlbot',
    extraJdbc: '',
    dbSchema: 'public',
    filename: '',
    sheets: [],
    mode: 'service_name',
    timeout: 30,
    lowVersion: true,
  }),
  encryptionKey,
  {
    mode: CryptoJS.mode.ECB,
    padding: CryptoJS.pad.Pkcs7,
  }
).toString()

const datasource = {
  id: 101,
  name: 'Orders Demo',
  type: 'postgresql',
  type_name: 'PostgreSQL',
  num: '0/2',
  description: 'Deterministic datasource for async sync UI',
  configuration: encryptedConfiguration,
}

const syncableTables = [
  { tableName: 'orders', tableComment: 'Orders' },
  { tableName: 'customers', tableComment: 'Customers' },
]

async function seedEnglishUser(page: Page) {
  await page.addInitScript(() => {
    const setCache = (key: string, value: unknown) => {
      localStorage.setItem(
        key,
        JSON.stringify({
          c: Date.now(),
          e: Date.now() + 24 * 60 * 60 * 1000,
          v: JSON.stringify(value),
        })
      )
    }

    setCache('user.token', 'e2e-ds-token')
    setCache('user.uid', '1')
    setCache('user.account', 'admin')
    setCache('user.name', 'Admin')
    setCache('user.oid', 'workspace-1')
    setCache('user.language', 'en')
    setCache('user.exp', 0)
    setCache('user.time', 0)
    setCache('user.weight', 1)
    setCache('user.origin', 0)
  })
}

async function installDatasourceMocks(page: Page) {
  await page.route('**/api/v1/user/info', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '1',
        account: 'admin',
        name: 'Admin',
        oid: 'workspace-1',
        language: 'en',
        exp: 0,
        time: 0,
        weight: 1,
        origin: 0,
      }),
    })
  })

  await page.route('**/api/v1/datasource/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([datasource]),
    })
  })

  await page.route('**/api/v1/datasource/get/101', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(datasource),
    })
  })

  await page.route('**/api/v1/datasource/check/**', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: 'true' })
  })
}

async function openChooseTablesDialog(page: Page) {
  const datasourceCard = page.locator('.card').filter({ hasText: 'Orders Demo' })
  await expect(datasourceCard).toBeVisible()

  await datasourceCard.click()

  const tablePage = page.locator('.data-table')
  await expect(tablePage).toBeVisible()
  await tablePage.locator('.select-table_top button').click()

  const chooseTablesDrawer = page.getByRole('dialog').filter({ hasText: 'Choose Tables' })
  await expect(chooseTablesDrawer).toBeVisible()
  return chooseTablesDrawer
}

test.describe('datasource async sync workflow', () => {
  test('submits async sync and shows terminal progress state', async ({ page }) => {
    let syncJobReads = 0

    await seedEnglishUser(page)
    await installBaseAppMocks(page)
    await installDatasourceMocks(page)

    await page.route('**/api/v1/datasource/tableList/101', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('**/api/v1/datasource/getTablesByConf', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(syncableTables),
      })
    })

    await page.route('**/api/v1/sync-jobs?datasource_id=101', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      })
    })

    await page.route('**/api/v1/sync-jobs', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 501,
          datasource_id: 101,
          status: 'pending',
          phase: 'submit',
          reused_active_job: false,
        }),
      })
    })

    await page.route('**/api/v1/sync-jobs/501', async (route) => {
      syncJobReads += 1
      const body =
        syncJobReads === 1
          ? {
              job_id: 501,
              datasource_id: 101,
              status: 'running',
              phase: 'stage',
              total_tables: 2,
              completed_tables: 1,
              failed_tables: 0,
              skipped_tables: 0,
              total_fields: 10,
              completed_fields: 5,
              current_table_name: 'customers',
              embedding_followup_status: null,
              error_summary: null,
              create_time: '2026-03-31T12:00:00',
              start_time: '2026-03-31T12:00:02',
              finish_time: null,
              update_time: '2026-03-31T12:00:03',
            }
          : {
              job_id: 501,
              datasource_id: 101,
              status: 'succeeded',
              phase: 'post_process',
              total_tables: 2,
              completed_tables: 2,
              failed_tables: 0,
              skipped_tables: 0,
              total_fields: 10,
              completed_fields: 10,
              current_table_name: null,
              embedding_followup_status: 'dispatched',
              error_summary: null,
              create_time: '2026-03-31T12:00:00',
              start_time: '2026-03-31T12:00:02',
              finish_time: '2026-03-31T12:00:08',
              update_time: '2026-03-31T12:00:08',
            }

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(body),
      })
    })

    await page.goto('/#/ds/index')
    const chooseTablesDialog = await openChooseTablesDialog(page)

    await chooseTablesDialog.locator('input[value="orders"]').evaluate((node) => {
      ;(node as HTMLInputElement).click()
    })
    await chooseTablesDialog.locator('input[value="customers"]').evaluate((node) => {
      ;(node as HTMLInputElement).click()
    })
    await page.getByRole('button', { name: 'Save' }).last().click()

    const syncJobDialog = page.locator('.ed-overlay-dialog').filter({ has: page.locator('.sync-job-panel') })
    const syncJobPanel = page.locator('.sync-job-panel')
    await expect(syncJobDialog).toBeVisible()
    await expect(syncJobPanel).toBeVisible()
    await expect(syncJobDialog).toContainText('Succeeded')
    await expect(syncJobDialog).toContainText('Successfully synced 2 tables.')
    await expect(syncJobPanel).toContainText('Embedding follow-up')
    await expect(syncJobPanel).toContainText('dispatched')
  })

  test('restores an active datasource sync job when reopening choose-tables drawer', async ({ page }) => {
    await seedEnglishUser(page)
    await installBaseAppMocks(page)
    await installDatasourceMocks(page)

    await page.route('**/api/v1/datasource/tableList/101', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([{ table_name: 'orders' }]),
      })
    })

    await page.route('**/api/v1/datasource/getTablesByConf', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(syncableTables),
      })
    })

    await page.route('**/api/v1/sync-jobs?datasource_id=101', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            job_id: 601,
            datasource_id: 101,
            status: 'running',
            phase: 'stage',
            total_tables: 2,
            completed_tables: 1,
            failed_tables: 0,
            skipped_tables: 0,
            total_fields: 6,
            completed_fields: 3,
            current_table_name: 'customers',
            embedding_followup_status: null,
            error_summary: null,
            create_time: '2026-03-31T12:10:00',
            start_time: '2026-03-31T12:10:02',
            finish_time: null,
            update_time: '2026-03-31T12:10:03',
          },
        ]),
      })
    })

    await page.route('**/api/v1/sync-jobs/601', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          job_id: 601,
          datasource_id: 101,
          status: 'running',
          phase: 'stage',
          total_tables: 2,
          completed_tables: 1,
          failed_tables: 0,
          skipped_tables: 0,
          total_fields: 6,
          completed_fields: 3,
          current_table_name: 'customers',
          embedding_followup_status: null,
          error_summary: null,
          create_time: '2026-03-31T12:10:00',
          start_time: '2026-03-31T12:10:02',
          finish_time: null,
          update_time: '2026-03-31T12:10:04',
        }),
      })
    })

    await page.goto('/#/ds/index')
    await openChooseTablesDialog(page)

    const syncJobDialog = page.locator('.ed-overlay-dialog').filter({ has: page.locator('.sync-job-panel') })
    const syncJobPanel = page.locator('.sync-job-panel')
    await expect(syncJobDialog).toBeVisible()
    await expect(syncJobPanel).toBeVisible()
    await expect(syncJobPanel).toContainText('Recovered the latest running sync job')
    await expect(syncJobPanel).toContainText('customers')
    await expect(page.getByRole('button', { name: 'Syncing...' })).toBeDisabled()
  })
})
