import { beforeEach, describe, expect, it, vi } from 'vitest'

const mockGet = vi.fn()

vi.mock('@/utils/request', () => ({
  request: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}))

import { getOpenClawMcpConfig } from '@/api/openclaw'

describe('openclaw API', () => {
  beforeEach(() => {
    mockGet.mockReset()
  })

  it('calls the MCP config endpoint', async () => {
    const mockResponse = {
      status: 'active',
      service: 'mcp',
      ready: true,
      setup_enabled: true,
      server_name: 'openclaw',
      bind_host: '0.0.0.0',
      port: 8001,
      path: '/mcp',
      base_url: 'http://localhost:8001',
      endpoint: 'http://localhost:8001/mcp',
      health_url: 'http://localhost:8001/health',
      auth_header: 'Authorization',
      auth_scheme: 'Bearer',
      operations: ['tools/list'],
      tool_names: ['mysqlbot_query'],
      issues: [],
    }

    mockGet.mockResolvedValue(mockResponse)

    const result = await getOpenClawMcpConfig()

    expect(mockGet).toHaveBeenCalledWith('/system/openclaw/mcp-config')
    expect(result).toEqual(mockResponse)
  })

  it('propagates request errors', async () => {
    mockGet.mockRejectedValue(new Error('Network error'))

    await expect(getOpenClawMcpConfig()).rejects.toThrow('Network error')
  })
})
