import { describe, expect, it } from 'vitest'

import { formatTimestamp } from '@/utils/date'

const pad = (value: number) => String(value).padStart(2, '0')

const formatWithLocalDateParts = (timestamp: number, format: string) => {
  const date = new Date(timestamp)

  return format.replace(/YYYY|MM|DD|HH|mm|ss/g, (token) => {
    switch (token) {
      case 'YYYY':
        return String(date.getFullYear())
      case 'MM':
        return pad(date.getMonth() + 1)
      case 'DD':
        return pad(date.getDate())
      case 'HH':
        return pad(date.getHours())
      case 'mm':
        return pad(date.getMinutes())
      case 'ss':
        return pad(date.getSeconds())
      default:
        return token
    }
  })
}

describe('formatTimestamp', () => {
  it('returns a dash for a zero timestamp', () => {
    expect(formatTimestamp(0)).toBe('-')
  })

  it('returns a dash for undefined and null timestamps', () => {
    expect(formatTimestamp(undefined as unknown as number)).toBe('-')
    expect(formatTimestamp(null as unknown as number)).toBe('-')
  })

  it('formats dates with the default YYYY-MM-DD format', () => {
    const timestamp = Date.UTC(2024, 4, 9, 3, 4, 5)

    expect(formatTimestamp(timestamp)).toBe(formatWithLocalDateParts(timestamp, 'YYYY-MM-DD'))
  })

  it('formats dates with a full datetime format', () => {
    const timestamp = Date.UTC(2024, 10, 13, 14, 15, 16)

    expect(formatTimestamp(timestamp, 'YYYY-MM-DD HH:mm:ss')).toBe(
      formatWithLocalDateParts(timestamp, 'YYYY-MM-DD HH:mm:ss')
    )
  })

  it('pads single-digit month and day values with leading zeros', () => {
    const timestamp = new Date(2024, 0, 2, 3, 4, 5).getTime()
    const formatted = formatTimestamp(timestamp, 'YYYY-MM-DD')
    const [, month, day] = formatted.split('-')

    expect(month).toHaveLength(2)
    expect(day).toHaveLength(2)
  })
})
