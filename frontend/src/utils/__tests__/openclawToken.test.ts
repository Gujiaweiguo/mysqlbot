import { describe, expect, it } from 'vitest'

import { buildOpenClawAuthHeaderValue, generateOpenClawToken } from '@/utils/openclawToken'

const decodeSegment = (segment: string) => {
  const normalized = segment.replace(/-/g, '+').replace(/_/g, '/')
  const padded = normalized.padEnd(Math.ceil(normalized.length / 4) * 4, '=')
  const decoded = atob(padded)

  const utf8 = decodeURIComponent(
    Array.from(decoded)
      .map((char) => `%${char.charCodeAt(0).toString(16).padStart(2, '0')}`)
      .join('')
  )

  return JSON.parse(utf8) as Record<string, string>
}

describe('openclawToken', () => {
  it('generates an HS256 token carrying the access_key payload', () => {
    const token = generateOpenClawToken({
      accessKey: 'demo-access-key',
      secretKey: 'demo-secret-key',
    })

    const [headerSegment, payloadSegment, signatureSegment] = token.split('.')

    expect(headerSegment).toBeTruthy()
    expect(payloadSegment).toBeTruthy()
    expect(signatureSegment).toBeTruthy()
    expect(decodeSegment(headerSegment)).toEqual({ alg: 'HS256', typ: 'JWT' })
    expect(decodeSegment(payloadSegment)).toEqual({ access_key: 'demo-access-key' })
  })

  it('builds the sk header value from the raw token', () => {
    const token = generateOpenClawToken({
      accessKey: 'demo-access-key',
      secretKey: 'demo-secret-key',
    })

    expect(buildOpenClawAuthHeaderValue(token)).toBe(`sk ${token}`)
  })
})
