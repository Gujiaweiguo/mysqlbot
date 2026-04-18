import CryptoJS from 'crypto-js'

interface OpenClawTokenOptions {
  accessKey: string
  secretKey: string
}

const JWT_HEADER = {
  alg: 'HS256',
  typ: 'JWT',
} as const

const toBase64Url = (value: string): string => {
  return value.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/u, '')
}

const encodeSegment = (value: Record<string, string>): string => {
  return toBase64Url(CryptoJS.enc.Base64.stringify(CryptoJS.enc.Utf8.parse(JSON.stringify(value))))
}

export const generateOpenClawToken = ({ accessKey, secretKey }: OpenClawTokenOptions): string => {
  const encodedHeader = encodeSegment(JWT_HEADER)
  const encodedPayload = encodeSegment({ access_key: accessKey })
  const signingInput = `${encodedHeader}.${encodedPayload}`
  const signature = toBase64Url(
    CryptoJS.enc.Base64.stringify(CryptoJS.HmacSHA256(signingInput, secretKey))
  )

  return `${signingInput}.${signature}`
}

export const buildOpenClawAuthHeaderValue = (token: string): string => {
  return `sk ${token}`
}
