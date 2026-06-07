import { LOCALE_STORAGE_KEY, isSupportedLocale, type SupportedLocaleCode } from './locales'

export const readStoredLocale = () => {
  if (typeof localStorage === 'undefined') return undefined
  return localStorage.getItem(LOCALE_STORAGE_KEY)
}

export const writeStoredLocale = (locale: SupportedLocaleCode) => {
  if (typeof localStorage === 'undefined') return
  localStorage.setItem(LOCALE_STORAGE_KEY, locale)
}

export const normalizeSelectedLocale = (locale: string): SupportedLocaleCode | undefined => {
  if (!isSupportedLocale(locale)) return undefined
  return locale
}
