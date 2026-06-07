<template>
  <section class='swap-faq micromeme-faq q-mb-xl' aria-labelledby='swap-faq-title'>
    <h2 id='swap-faq-title' class='faq-title q-ma-none'>{{ t('faq.title') }}</h2>
    <div class='q-mt-lg'>
      <q-expansion-item
        v-for='item in faqItems'
        :key='item.question'
        class='faq-row'
        header-class='faq-item-header'
        expand-icon-class='text-neutral'
        expand-separator
        :aria-label='item.question'
      >
        <template #header>
          <div class='faq-header row items-center full-width'>
            <div class='faq-question text-light'>
              {{ item.question }}
            </div>
          </div>
        </template>
        <div class='faq-answer q-pb-lg text-neutral font-size-16'>
          {{ item.answer }}
        </div>
      </q-expansion-item>
    </div>
  </section>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { useMeta } from 'quasar'
import { useI18n } from 'vue-i18n'

interface FaqItem {
  question: string
  answer: string
}

const { t, tm } = useI18n()

const faqItems = computed(() => tm('faq.items') as FaqItem[])

useMeta(() => ({
  script: {
    faqStructuredData: {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faqItems.value.map((item) => ({
          '@type': 'Question',
          name: item.question,
          acceptedAnswer: {
            '@type': 'Answer',
            text: item.answer,
          },
        })),
      }),
    },
  },
}))
</script>

<style scoped lang='sass'>
.faq-title
  font-size: 34px
  line-height: 1.1
  letter-spacing: 0
  font-weight: 500
  padding: 0 !important

.swap-faq
  margin-top: 104px

.faq-row
  border-top: 1px solid rgba(255, 255, 255, 0.08)

  &:last-child
    border-bottom: 1px solid rgba(255, 255, 255, 0.08)

.faq-header
  padding: 12px 0
  min-height: 0
  align-items: center
  width: 100%

.faq-question
  font-size: 22px
  font-weight: 400
  line-height: 1.3
  letter-spacing: 0
  padding-right: 8px
  flex: 1 1 auto
  min-width: 0
  white-space: normal
  overflow-wrap: anywhere

.faq-answer
  line-height: 1.85
  padding: 0 8px 24px 0
  font-size: 21px
  max-width: none
  width: 100%

::v-deep(.swap-faq .q-expansion-item__toggle-icon)
  font-size: 32px

:global(.micromeme-faq .faq-item-header.q-item)
  min-height: auto
  padding: 0 !important
  align-items: center

::v-deep(.swap-faq .q-item)
  min-height: auto
  padding: 0 !important
  align-items: center

::v-deep(.swap-faq .q-item__section)
  min-width: 0
  flex: 1 1 auto
  padding-left: 0 !important
  padding-right: 0 !important

::v-deep(.swap-faq .q-item__section--side)
  align-self: center
  flex: 0 0 auto
  padding-left: 6px
  padding-right: 0

::v-deep(.swap-faq .q-focus-helper)
  display: none

::v-deep(.swap-faq .q-expansion-item__content)
  padding-left: 0 !important
  padding-right: 0 !important

::v-deep(.swap-faq .q-expansion-item__container)
  transition: opacity 0.2s ease

@media (max-width: 1023px)
  .swap-faq
    margin-top: 88px

  .faq-title
    font-size: 30px

  .faq-question
    font-size: 19px

  .faq-answer
    font-size: 19px
    padding-right: 0

@media (max-width: 599px)
  .swap-faq
    margin-top: 72px

  .faq-title
    font-size: 27px

  .faq-question
    font-size: 18px

  .faq-answer
    font-size: 18px
    padding-bottom: 20px
</style>
