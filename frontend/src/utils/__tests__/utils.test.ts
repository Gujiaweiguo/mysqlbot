import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('@/utils/useCache', () => ({
  useCache: () => ({
    wsCache: {
      get: vi.fn(),
      set: vi.fn(),
      delete: vi.fn(),
    },
  }),
}))

vi.mock('less/lib/less/functions/color.js', () => ({ default: {} }))
vi.mock('less/lib/less/tree/color.js', () => ({ default: class MockColorTree {} }))

import {
  colorStringToHex,
  datetimeFormat,
  formatArg,
  getQueryString,
  isBtnShow,
  setSize,
} from '@/utils/utils'

describe('utils helpers', () => {
  const originalLocation = window.location.href
  const originalTop = window.top
  const originalSelf = window.self

  beforeEach(() => {
    window.history.replaceState({}, '', '/')
    Object.defineProperty(window, 'top', { configurable: true, value: originalTop })
    Object.defineProperty(window, 'self', { configurable: true, value: originalSelf })
  })

  afterEach(() => {
    window.history.replaceState({}, '', originalLocation)
    Object.defineProperty(window, 'top', { configurable: true, value: originalTop })
    Object.defineProperty(window, 'self', { configurable: true, value: originalSelf })
  })

  it('formats byte sizes into human-readable units', () => {
    expect(setSize(500)).toBe('500B')
    expect(setSize(1500)).toBe('1.46KB')
    expect(setSize(1500000)).toBe('1.43MB')
    expect(setSize(1500000000)).toBe('1.40GB')
  })

  it('converts color strings to hex values', () => {
    expect(colorStringToHex('#ff0000')).toBe('#ff0000')
    expect(colorStringToHex('rgb(255, 0, 0)')).toBe('#FF0000')
    expect(colorStringToHex('rgba(255, 0, 0, 0.5)')).toBe('#FF000080')
    expect(colorStringToHex('not-a-color')).toBeNull()
  })

  it('reads query-string values from the current URL', () => {
    window.history.replaceState({}, '', '/?foo=bar&baz=qux')

    expect(getQueryString('foo')).toBe('bar')
    expect(getQueryString('missing')).toBeNull()
  })

  it('shows or hides buttons according to explicit flag values', () => {
    expect(isBtnShow(undefined as unknown as string)).toBe(true)
    expect(isBtnShow('0')).toBe(true)
    expect(isBtnShow('1')).toBe(false)
  })

  it('uses iframe detection for non-standard button visibility flags', () => {
    Object.defineProperty(window, 'top', { configurable: true, value: {} })
    Object.defineProperty(window, 'self', { configurable: true, value: window })
    expect(isBtnShow('custom')).toBe(false)

    Object.defineProperty(window, 'top', { configurable: true, value: window })
    Object.defineProperty(window, 'self', { configurable: true, value: window })
    expect(isBtnShow('custom')).toBe(true)
  })

  it('formats valid timestamps and returns invalid inputs as-is', () => {
    expect(datetimeFormat('invalid-date')).toBe('invalid-date')
    expect(datetimeFormat(new Date(2024, 0, 2, 3, 4, 5))).toBe('2024-01-02 03:04:05')
  })

  it('parses mapped argument values and preserves other strings', () => {
    expect(formatArg('true')).toBe(true)
    expect(formatArg('false')).toBe(false)
    expect(formatArg('1')).toBe(1)
    expect(formatArg('0')).toBe(0)
    expect(formatArg('')).toBe(false)
    expect(formatArg('hello')).toBe('hello')
  })
})
