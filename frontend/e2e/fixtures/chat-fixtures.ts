import type { Page, Route } from '@playwright/test'

type ChatRecordPayload = {
  id: number
  chat_id: number
  create_time?: string
  question: string
  sql?: string
  data?: {
    fields: string[]
    data: Array<Record<string, string | number>>
    limit?: number
    datasource?: number
    sql?: string
  }
  chart?: string
  datasource?: number
  datasource_name?: string
  first_chat?: boolean
  recommended_question?: string
  finish?: boolean
}

type ChatInfoPayload = {
  id: number
  brief: string
  datasource?: number
  datasource_name?: string
  ds_type?: string
  records: ChatRecordPayload[]
  create_time?: string
}

const userInfo = {
  id: '1',
  account: 'admin',
  name: 'Admin',
  oid: 'workspace-1',
  language: 'zh-CN',
  exp: 0,
  time: 0,
  weight: 1,
  origin: 0,
}

const e2eToken = 'eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxIn0.signature'

const datasource = {
  id: 101,
  name: 'Orders Demo',
  type: 'postgresql',
  type_name: 'PostgreSQL',
  num: '3 tables',
  description: 'Deterministic test datasource',
}

const switchedDatasource = {
  id: 202,
  name: 'CRM Demo',
  type: 'mysql',
  type_name: 'MySQL',
  num: '2 tables',
  description: 'Secondary deterministic datasource',
}

const emptyChatInfo = {
  id: 9001,
  brief: 'New chat',
  datasource: datasource.id,
  datasource_name: datasource.name,
  ds_type: datasource.type,
  records: [
    {
      id: 6001,
      chat_id: 9001,
      create_time: '2026-03-17 10:00:00',
      question: '',
      first_chat: true,
      recommended_question: '["Show revenue by month"]',
      finish: true,
    },
  ],
  create_time: '2026-03-17 10:00:00',
} satisfies ChatInfoPayload

const switchedEmptyChatInfo = {
  id: 9003,
  brief: 'Switched chat',
  datasource: switchedDatasource.id,
  datasource_name: switchedDatasource.name,
  ds_type: switchedDatasource.type,
  records: [
    {
      id: 6003,
      chat_id: 9003,
      create_time: '2026-03-17 10:05:00',
      question: '',
      first_chat: true,
      recommended_question: '["Show opportunity pipeline"]',
      finish: true,
    },
  ],
  create_time: '2026-03-17 10:05:00',
} satisfies ChatInfoPayload

const historyChatInfo = {
  id: 9002,
  brief: 'Revenue trend',
  datasource: datasource.id,
  datasource_name: datasource.name,
  ds_type: datasource.type,
  create_time: '2026-03-16 10:00:00',
  records: [
    {
      id: 501,
      chat_id: 9002,
      question: 'Show revenue by month',
      sql: 'SELECT month, revenue FROM revenue_by_month',
      data: {
        fields: ['month', 'revenue'],
        data: [
          { month: 'Jan', revenue: 120 },
          { month: 'Feb', revenue: 140 },
        ],
        limit: 50,
        datasource: datasource.id,
        sql: 'SELECT month, revenue FROM revenue_by_month',
      },
      chart: JSON.stringify({
        type: 'table',
        columns: [
          { name: 'Month', value: 'month' },
          { name: 'Revenue', value: 'revenue' },
        ],
      }),
      datasource: datasource.id,
      datasource_name: datasource.name,
      recommended_question: '["Show top customers"]',
      finish: true,
    },
  ],
} satisfies ChatInfoPayload

function cacheEnvelope<T>(value: T) {
  return JSON.stringify({
    c: Date.now(),
    e: Date.now() + 24 * 60 * 60 * 1000,
    v: JSON.stringify(value),
  })
}

export async function seedAuthenticatedUser(page: Page): Promise<void> {
  await page.addInitScript(
    ({ user, token }) => {
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

      try {
        setCache('user.token', token)
        setCache('user.uid', user.id)
        setCache('user.account', user.account)
        setCache('user.name', user.name)
        setCache('user.oid', user.oid)
        setCache('user.language', user.language)
        setCache('user.exp', user.exp)
        setCache('user.time', user.time)
        setCache('user.weight', user.weight)
        setCache('user.origin', user.origin)
      } catch {
        return
      }
    },
    { user: userInfo, token: e2eToken }
  )
}

export async function installBaseAppMocks(page: Page): Promise<void> {
  await installLicenseGeneratorMock(page)
  await installStandardBaseAppRoutes(page)
}

async function installStandardBaseAppRoutes(page: Page): Promise<void> {
  await page.route('**/api/v1/user/info', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(userInfo),
    })
  })

  await page.route('**/api/v1/system/aimodel/default', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 1, name: 'Mock Default Model' }),
    })
  })

  await page.route('**/api/v1/system/appearance/ui', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) })
  })

  await page.route('**/api/v1/user/ws', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([{ id: 1, name: 'Default Workspace' }]),
    })
  })

  await page.route('**/api/v1/system/license/version', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ version: 'e2e-mock' }),
    })
  })

  await page.route('**/api/v1/system/license', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ valid: true }),
    })
  })

  await page.route('**/api/v1/system/parameter/chat', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { pkey: 'chat.expand_thinking_block', pval: 'false' },
        { pkey: 'chat.limit_rows', pval: 'true' },
      ]),
    })
  })
}

export async function installLicenseGeneratorMock(
  page: Page,
  options?: {
    scriptBody?: string
  }
): Promise<void> {
  const scriptBody =
    options?.scriptBody ??
    `var LicenseGenerator = {
      init: async function () { return true },
      getLicense: function () { return { status: 'invalid' } },
      generateRouters: function () { return undefined },
      sqlbotEncrypt: function (value) { return value },
    };
    window.LicenseGenerator = LicenseGenerator;
    globalThis.LicenseGenerator = LicenseGenerator;`

  await page.addInitScript(scriptBody)
}

export async function installLicenseGeneratorContractMocks(page: Page): Promise<void> {
  await installLicenseGeneratorMock(page, {
    scriptBody: `window.__licenseContract = {
      initArgs: [],
      generateRoutersCalls: 0,
      encryptedValues: [],
      getLicenseCalls: 0,
    };
    var LicenseGenerator = {
      init: async function (baseUrl) {
        window.__licenseContract.initArgs.push(baseUrl);
        return true;
      },
      getLicense: function () {
        window.__licenseContract.getLicenseCalls += 1;
        return { status: 'invalid' };
      },
      generateRouters: function () {
        window.__licenseContract.generateRoutersCalls += 1;
        return undefined;
      },
      sqlbotEncrypt: function (value) {
        var encrypted = 'enc::' + value;
        window.__licenseContract.encryptedValues.push({ input: value, output: encrypted });
        return encrypted;
      },
    };
    window.LicenseGenerator = LicenseGenerator;
    globalThis.LicenseGenerator = LicenseGenerator;`,
  })

  await page.route('**/api/v1/login/access-token', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 0, data: { token: 'mock-token' } }),
    })
  })

  await page.route('**/api/v1/system/aimodel', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 0, data: { id: 1 } }),
      })
      return
    }

    await route.fallback()
  })

  await installStandardBaseAppRoutes(page)
}

export async function installChatFlowMocks(page: Page): Promise<void> {
  await installBaseAppMocks(page)
  await installSharedChatMocks(page)

  await installSuccessChatRecordMocks(page)

  await page.route('**/api/v1/chat/question', async (route) => {
    await fulfillStreaming(route, [
      { type: 'id', id: 7001 },
      { type: 'question', question: 'Show revenue by month' },
      {
        type: 'datasource',
        id: datasource.id,
        datasource_name: datasource.name,
        engine_type: 'PostgreSQL',
      },
      { type: 'sql-result', content: 'SELECT month, revenue', reasoning_content: 'Drafting SQL' },
      { type: 'info', msg: 'sql generated' },
      { type: 'sql', content: 'SELECT month, revenue FROM revenue_by_month' },
      { type: 'sql-data', content: 'execute-success' },
      { type: 'chart-result', content: 'Table chart', reasoning_content: 'Formatting chart' },
      { type: 'info', msg: 'chart generated' },
      {
        type: 'chart',
        content: JSON.stringify({
          type: 'table',
          columns: [
            { name: 'Month', value: 'month' },
            { name: 'Revenue', value: 'revenue' },
          ],
        }),
      },
      { type: 'finish' },
    ])
  })
}

export async function installAssistantDirectEntryMocks(page: Page): Promise<void> {
  await installBaseAppMocks(page)
  await installSuccessChatRecordMocks(page)

  await page.route('**/api/v1/chat/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  })

  await page.route('**/api/v1/system/assistant/validator**', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ valid: true, id_match: true, domain_match: true, token: e2eToken }),
    })
  })

  await page.route('**/api/v1/system/assistant/77', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 77,
        name: 'Assistant Demo',
        type: 0,
        domain: 'http://example.com',
        configuration: JSON.stringify({
          auto_ds: true,
          default_datasource_id: datasource.id,
          datasource_ids: [datasource.id, switchedDatasource.id],
          workspace_ids: [1],
        }),
      }),
    })
  })

  await page.route('**/api/v1/system/assistant/ds', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([datasource, switchedDatasource]),
    })
  })

  await page.route('**/api/v1/datasource/check/*', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: 'true' })
  })

  await page.route('**/api/v1/chat/assistant/start', async (route) => {
    const payload = route.request().postDataJSON() as { datasource?: number }
    const selectedDatasourceId = payload?.datasource
    const body = selectedDatasourceId === switchedDatasource.id ? switchedEmptyChatInfo : emptyChatInfo
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body),
    })
  })

  await page.route('**/api/v1/recommended_problem/get_datasource_recommended_base/*', async (route) => {
    const url = route.request().url()
    const isSwitchedDatasource = url.endsWith(`/${switchedDatasource.id}`)
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        recommended_config: 2,
        questions: isSwitchedDatasource
          ? '["Show opportunity pipeline"]'
          : '["Show revenue by month"]',
      }),
    })
  })
}

export async function installChatErrorFlowMocks(page: Page): Promise<void> {
  await installBaseAppMocks(page)
  await installSharedChatMocks(page)

  await page.route('**/api/v1/chat/question', async (route) => {
    await fulfillStreaming(route, [
      { type: 'id', id: 7002 },
      { type: 'question', question: 'Show revenue by month' },
      {
        type: 'datasource',
        id: datasource.id,
        datasource_name: datasource.name,
        engine_type: 'PostgreSQL',
      },
      { type: 'error', content: 'Simulated database connection failure' },
    ])
  })
}

export async function installChatReplayFlowMocks(page: Page): Promise<void> {
  await installBaseAppMocks(page)
  await installSharedChatMocks(page)
  await installSuccessChatRecordMocks(page)

  await page.route('**/api/v1/chat/question', async (route) => {
    await fulfillStreaming(route, [
      { type: 'id', id: 7003 },
      { type: 'question', question: 'Show top customers' },
      {
        type: 'datasource',
        id: datasource.id,
        datasource_name: datasource.name,
        engine_type: 'PostgreSQL',
      },
      {
        type: 'sql-result',
        content: 'SELECT customer, revenue',
        reasoning_content: 'Drafting follow-up SQL',
      },
      { type: 'info', msg: 'sql generated' },
      {
        type: 'sql',
        content:
          'SELECT customer, SUM(revenue) AS revenue FROM orders GROUP BY customer ORDER BY revenue DESC LIMIT 10',
      },
      { type: 'sql-data', content: 'execute-success' },
      {
        type: 'chart-result',
        content: 'Replay chart',
        reasoning_content: 'Formatting replay chart',
      },
      { type: 'info', msg: 'chart generated' },
      {
        type: 'chart',
        content: JSON.stringify({
          type: 'table',
          columns: [
            { name: 'Customer', value: 'customer' },
            { name: 'Revenue', value: 'revenue' },
          ],
        }),
      },
      { type: 'finish' },
    ])
  })

  await page.route('**/api/v1/chat/record/7003/data', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        fields: ['customer', 'revenue'],
        data: [
          { customer: 'Acme Corp', revenue: 5000 },
          { customer: 'Globex', revenue: 4200 },
        ],
        limit: 50,
        datasource: datasource.id,
        sql: 'SELECT customer, SUM(revenue) AS revenue FROM orders GROUP BY customer ORDER BY revenue DESC LIMIT 10',
      }),
    })
  })

  await page.route('**/api/v1/chat/record/7003/usage', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        duration: 1,
        finish_time: '2026-03-17 10:00:02',
        total_tokens: 35,
        steps: [],
      }),
    })
  })

  await page.route('**/api/v1/chat/recommend_questions/7003*', async (route) => {
    await fulfillStreaming(route, [
      { type: 'recommended_question', content: '["Show monthly trends"]' },
    ])
  })
}

async function installSharedChatMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/chat/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([historyChatInfo]),
    })
  })

  await page.route('**/api/v1/datasource/list', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([datasource]),
    })
  })

  await page.route('**/api/v1/datasource/check/*', async (route) => {
    await route.fulfill({ status: 200, contentType: 'application/json', body: 'true' })
  })

  await page.route('**/api/v1/chat/start', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(emptyChatInfo),
    })
  })

  await page.route('**/api/v1/chat/9002', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(historyChatInfo),
    })
  })
}

async function installSuccessChatRecordMocks(page: Page): Promise<void> {
  await page.route('**/api/v1/chat/record/7001/data', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        fields: ['month', 'revenue'],
        data: [
          { month: 'Jan', revenue: 120 },
          { month: 'Feb', revenue: 140 },
        ],
        limit: 50,
        datasource: datasource.id,
        sql: 'SELECT month, revenue FROM revenue_by_month',
      }),
    })
  })

  await page.route('**/api/v1/chat/record/7001/usage', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        duration: 1,
        finish_time: '2026-03-17 10:00:01',
        total_tokens: 42,
        steps: [],
      }),
    })
  })

  await page.route('**/api/v1/chat/recommend_questions/7001*', async (route) => {
    await fulfillStreaming(route, [
      {
        type: 'recommended_question_result',
        content: 'thinking',
        reasoning_content: 'mock',
      },
      { type: 'recommended_question', content: '["Show top customers"]' },
    ])
  })
}

async function fulfillStreaming(
  route: Route,
  events: Array<Record<string, unknown>>
): Promise<void> {
  const body = events.map((event) => `data:${JSON.stringify(event)}\n\n`).join('')
  await route.fulfill({
    status: 200,
    contentType: 'text/event-stream',
    body,
  })
}

export { cacheEnvelope }
