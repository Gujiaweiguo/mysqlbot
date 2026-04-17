import { request } from '@/utils/request'

export interface OpenClawMcpConfigResponse {
  status: string
  service: string
  ready: boolean
  setup_enabled: boolean
  server_name: string
  bind_host: string
  port: number
  path: string
  base_url: string
  endpoint: string
  health_url: string
  auth_header: string
  auth_scheme: string
  operations: string[]
  tool_names: string[]
  issues: string[]
}

export const getOpenClawMcpConfig = () =>
  request.get<OpenClawMcpConfigResponse>('/system/openclaw/mcp-config')
