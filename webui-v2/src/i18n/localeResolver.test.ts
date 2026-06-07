import { describe, expect, test } from 'bun:test'

import { resolveInitialLocale, resolveSupportedLocale } from './localeResolver'
import { selectableLocales, supportedLocales } from './locales'

describe('localeResolver', () => {
  test('uses stored locale before browser locale', () => {
    expect(
      resolveInitialLocale({
        storedLocale: 'zh-TW',
        browserLocales: ['en-US'],
        browserLocale: 'en-US',
      }),
    ).toBe('zh-TW')
  })

  test('falls back from invalid stored locale to browser locale', () => {
    expect(
      resolveInitialLocale({
        storedLocale: 'fr-FR',
        browserLocales: ['zh-HK'],
        browserLocale: 'en-US',
      }),
    ).toBe('zh-TW')
  })

  test('matches English language family to en-US', () => {
    expect(resolveSupportedLocale('en-US')).toBe('en-US')
    expect(resolveSupportedLocale('en-GB')).toBe('en-US')
    expect(resolveSupportedLocale('en-AU')).toBe('en-US')
  })

  test('matches non-mainland Chinese locales to zh-TW', () => {
    expect(resolveSupportedLocale('zh-TW')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-HK')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-MO')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-SG')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-Hant')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-Hant-HK')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-Hans')).toBe('zh-TW')
    expect(resolveSupportedLocale('zh-Hans-SG')).toBe('zh-TW')
  })

  test('does not match mainland Chinese locales', () => {
    expect(resolveSupportedLocale('zh-CN')).toBe(undefined)
    expect(resolveSupportedLocale('zh-Hans-CN')).toBe(undefined)
  })

  test('falls back to en-US when no stored or browser locale is supported', () => {
    expect(
      resolveInitialLocale({
        browserLocales: ['fr-FR', 'ja-JP'],
        browserLocale: 'ko-KR',
      }),
    ).toBe('en-US')
  })

  test('selectable locales only include complete locales', () => {
    expect(selectableLocales()).toEqual(supportedLocales.filter((locale) => locale.complete))
    expect(selectableLocales().map((locale) => locale.code)).toEqual(['en-US', 'zh-TW'])
  })
})
