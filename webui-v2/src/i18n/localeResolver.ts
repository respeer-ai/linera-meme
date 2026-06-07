import { FALLBACK_LOCALE, isSupportedLocale, type SupportedLocaleCode } from './locales'

interface ResolveLocaleInput {
  storedLocale?: string | null | undefined
  browserLocales?: readonly string[]
  browserLocale?: string | undefined
}

export const resolveInitialLocale = ({
  storedLocale,
  browserLocales = [],
  browserLocale,
}: ResolveLocaleInput): SupportedLocaleCode => {
  const stored = resolveSupportedLocale(storedLocale)
  if (stored) return stored

  for (const locale of browserLocales) {
    const resolved = resolveSupportedLocale(locale)
    if (resolved) return resolved
  }

  return resolveSupportedLocale(browserLocale) || FALLBACK_LOCALE
}

export const resolveSupportedLocale = (locale: string | undefined | null): SupportedLocaleCode | undefined => {
  if (!locale) return undefined

  const normalized = locale.trim()
  if (isSupportedLocale(normalized)) return normalized

  const lower = normalized.toLowerCase()
  if (lower.startsWith('en-')) return 'en-US'
  if (lower === 'zh-cn' || lower.endsWith('-cn')) return undefined

  if (lower === 'zh-tw' || lower === 'zh-hk' || lower === 'zh-mo' || lower === 'zh-sg') {
    return 'zh-TW'
  }
  if (lower.startsWith('zh-hant')) return 'zh-TW'
  if (lower === 'zh-hans' || lower.startsWith('zh-hans-')) return 'zh-TW'

  return undefined
}
