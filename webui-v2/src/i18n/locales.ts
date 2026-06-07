export const LOCALE_STORAGE_KEY = 'micromeme.locale'
export const FALLBACK_LOCALE = 'en-US'

export type SupportedLocaleCode = 'en-US' | 'zh-TW'

export interface SupportedLocale {
  code: SupportedLocaleCode
  label: string
  nativeLabel: string
  icon: string
  complete: boolean
}

export const supportedLocales: SupportedLocale[] = [
  {
    code: 'en-US',
    label: 'English',
    nativeLabel: 'English',
    icon: '🇺🇸',
    complete: true,
  },
  {
    code: 'zh-TW',
    label: 'Traditional Chinese',
    nativeLabel: '繁體中文',
    icon: '🇨🇳',
    complete: true,
  },
]

export const selectableLocales = () => supportedLocales.filter((locale) => locale.complete)

export const isSupportedLocale = (locale: string | undefined): locale is SupportedLocaleCode =>
  selectableLocales().some((supported) => supported.code === locale)
