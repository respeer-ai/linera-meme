<template>
  <q-select
    filled
    dense
    borderless
    emit-value
    map-options
    dropdown-icon='language'
    v-model='selectedLocale'
    :options='languageOptions'
    class='language-select'
    popup-content-class='bg-dark-secondary'
    @update:model-value='selectLocale'
  >
    <template #prepend>
      <span class='language-option-icon'>{{ activeLocaleIcon }}</span>
    </template>
    <template #option='scope'>
      <q-item v-bind='scope.itemProps'>
        <q-item-section avatar>
          <span class='language-option-icon'>{{ scope.opt.icon }}</span>
        </q-item-section>
        <q-item-section>
          <q-item-label>{{ scope.opt.label }}</q-item-label>
          <q-item-label caption>{{ scope.opt.caption }}</q-item-label>
        </q-item-section>
        <q-item-section v-if='scope.opt.value === activeLocale' side>
          <q-icon name='check' color='secondary' />
        </q-item-section>
      </q-item>
    </template>
  </q-select>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { selectableLocales, type SupportedLocaleCode } from 'src/i18n/locales'
import { writeStoredLocale } from 'src/i18n/runtimeLocale'

const { locale } = useI18n()

const activeLocale = computed(() => locale.value)
const activeLocaleOption = computed(() =>
  selectableLocales().find((localeOption) => localeOption.code === activeLocale.value),
)
const activeLocaleIcon = computed(() => activeLocaleOption.value?.icon || '')
const selectedLocale = computed({
  get: () => activeLocale.value,
  set: (code: string) => selectLocale(code as SupportedLocaleCode),
})
const languageOptions = computed(() =>
  selectableLocales().map((localeOption) => ({
    label: localeOption.nativeLabel,
    caption: localeOption.label,
    value: localeOption.code,
    icon: localeOption.icon,
  })),
)

const selectLocale = (code: SupportedLocaleCode) => {
  locale.value = code
  writeStoredLocale(code)
}
</script>

<style scoped lang='sass'>
.language-select
  min-width: 132px

.language-option-icon
  font-size: 20px
  line-height: 1
</style>
