# WebUI Internationalization

Type: Context
Audience: Coding assistants
Authority: High

## Purpose

Define the WEBUI-001 phase-1 i18n scope for `webui-v2/`.

## Facts

- `webui-v2` already has `vue-i18n` dependency and Quasar boot wiring.
- Current locale resources are placeholder-only.
- Product UI text is mostly hard-coded.
- Phase 1 supports only:
  - `en-US`
  - `zh-TW`
- Do not support `zh-CN`.
- Do not map mainland Chinese locales to Chinese.
- Page-local language selection affects only this app.
- Page-local language selection must not change browser or operating-system language.

## Locale Resolution

Priority:

1. Stored app locale from `localStorage['micromeme.locale']`
2. Browser locale from `navigator.languages` / `navigator.language`
3. Fallback `en-US`

Supported matching:

- `en-US` -> `en-US`
- `en-*` -> `en-US`
- `zh-TW` -> `zh-TW`
- `zh-HK` -> `zh-TW`
- `zh-MO` -> `zh-TW`
- `zh-Hant*` -> `zh-TW`
- `zh-Hans` -> `zh-TW`
- `zh-Hans-*` except `zh-Hans-CN` -> `zh-TW`
- `zh-SG` -> `zh-TW`

Unsupported matching:

- `zh-CN` -> fallback path, not `zh-TW`
- `zh-*-CN` -> fallback path, not `zh-TW`
- Unknown locale -> fallback `en-US`

## Locale Registry

Required phase-1 locales:

- `en-US`
  - label: `English`
  - native label: `English`
  - complete: `true`
- `zh-TW`
  - label: `Traditional Chinese`
  - native label: `繁體中文`
  - complete: `true`

Only `complete: true` locales may appear in the UI.

## Header Switch

- Add a compact language dropdown in `HeaderView.vue`.
- Place it next to the current dark-mode switch.
- Do not add a standalone language settings page in phase 1.
- Use a language icon button trigger.
- Menu options:
  - `English`
  - `繁體中文`
- Show selected/check state for the active locale.
- On selection:
  - update `i18n.global.locale.value`
  - write `localStorage['micromeme.locale']`

## Phase-1 Copy Scope

Migrate only stable shared text:

- `common.failed`
- `common.success`
- `navigation.*`
- `header.theme`
- `header.language`
- `language.*`

Do not migrate these in WEBUI-001:

- transactions list copy; belongs to WEBUI-002
- FAQ copy; belongs to WEBUI-003
- Add Liquidity / Remove Liquidity page copy; belongs to WEBUI-004
- side drawer copy; belongs to WEBUI-005

## Implementation Files

Expected implementation files:

- `webui-v2/src/i18n/en-US/index.ts`
- `webui-v2/src/i18n/zh-TW/index.ts`
- `webui-v2/src/i18n/index.ts`
- `webui-v2/src/i18n/locales.ts`
- `webui-v2/src/i18n/localeResolver.ts`
- `webui-v2/src/boot/i18n.ts`
- `webui-v2/src/components/header/LanguageSwitchView.vue`
- `webui-v2/src/components/header/HeaderView.vue`
- `webui-v2/src/components/header/TabsView.vue`

## Validation

Required tests:

- stored `zh-TW` wins over browser locale
- invalid stored locale falls back to browser locale
- `zh-HK`, `zh-MO`, and `zh-Hant*` resolve to `zh-TW`
- `zh-CN` and `zh-*-CN` do not resolve to `zh-TW`
- `zh-Hans`, `zh-Hans-SG`, and `zh-SG` resolve to `zh-TW`
- unsupported browser locale falls back to `en-US`
- selectable locales include only `complete: true`

Required commands:

- `bun test`
- `bun run lint`
