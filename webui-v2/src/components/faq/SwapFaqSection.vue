<template>
  <section class='swap-faq micromeme-faq q-mb-xl' aria-labelledby='swap-faq-title'>
    <div class='faq-layout'>
      <aside class='faq-aside'>
        <div class='faq-kicker'>MicroMeme protocol notes</div>
        <h2 id='swap-faq-title' class='faq-title q-ma-none'>{{ t('faq.title') }}</h2>
        <p class='faq-intro q-ma-none text-neutral'>{{ t('faq.intro') }}</p>
        <div class='faq-topics' aria-label='FAQ topics'>
          <span
            v-for='topic in faqTopics'
            :key='topic'
            class='faq-topic'
          >
            {{ topic }}
          </span>
        </div>
      </aside>

      <div class='faq-list' aria-label='MicroMeme FAQ list'>
        <q-expansion-item
          v-for='item in faqItems'
          :key='item.question'
          class='faq-row'
          header-class='faq-item-header'
          expand-icon-class='text-neutral'
          :aria-label='item.question'
        >
          <template #header>
            <div class='faq-header'>
              <div class='faq-category'>{{ item.category }}</div>
              <div class='faq-question text-light'>
                {{ item.question }}
              </div>
            </div>
          </template>
          <div class='faq-answer text-neutral'>
            {{ item.answer }}
          </div>
        </q-expansion-item>
      </div>
    </div>
  </section>
</template>

<script setup lang='ts'>
import { computed } from 'vue'
import { useMeta } from 'quasar'
import { useI18n } from 'vue-i18n'

interface FaqItem {
  category: string
  question: string
  answer: string
}

const { t, tm } = useI18n()

const faqItems = computed(() => tm('faq.items') as FaqItem[])
const faqTopics = computed(() => tm('faq.topics') as string[])

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
.swap-faq
  margin-top: 104px

.faq-layout
  display: grid
  grid-template-columns: minmax(280px, 360px) minmax(0, 1fr)
  gap: 56px
  align-items: start

.faq-aside
  position: sticky
  top: 96px
  padding-top: 2px

.faq-kicker
  color: var(--q-secondary)
  font-size: 13px
  font-weight: 700
  line-height: 1.2
  letter-spacing: 0
  text-transform: uppercase

.faq-title
  font-size: 34px
  line-height: 1.1
  letter-spacing: 0
  font-weight: 500
  padding: 0 !important
  margin-top: 14px !important

.faq-intro
  margin-top: 20px !important
  font-size: 18px
  line-height: 1.75
  max-width: 330px

.faq-topics
  display: flex
  flex-wrap: wrap
  gap: 8px
  margin-top: 24px

.faq-topic
  border: 1px solid rgba(255, 255, 255, 0.12)
  border-radius: 999px
  color: var(--q-light)
  background: rgba(255, 255, 255, 0.035)
  font-size: 13px
  font-weight: 600
  line-height: 1
  padding: 9px 12px

.faq-list
  border-top: 1px solid rgba(255, 255, 255, 0.1)

.faq-row
  border-bottom: 1px solid rgba(255, 255, 255, 0.1)
  transition: background-color 0.18s ease, border-color 0.18s ease

  &:hover
    background: rgba(255, 255, 255, 0.025)

  &.q-expansion-item--expanded
    background: rgba(255, 255, 255, 0.04)
    border-color: rgba(255, 255, 255, 0.16)

.faq-header
  display: grid
  grid-template-columns: 128px minmax(0, 1fr)
  gap: 24px
  align-items: baseline
  width: 100%
  padding: 22px 0

.faq-category
  color: var(--q-secondary)
  font-size: 13px
  font-weight: 700
  line-height: 1.2
  letter-spacing: 0
  text-transform: uppercase
  white-space: nowrap

.faq-question
  font-size: 22px
  font-weight: 400
  line-height: 1.35
  letter-spacing: 0
  padding-right: 8px
  min-width: 0
  white-space: normal
  overflow-wrap: anywhere

.faq-answer
  line-height: 1.85
  padding: 0 56px 28px 152px
  font-size: 20px
  max-width: 920px
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
  padding-left: 12px
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

  .faq-layout
    grid-template-columns: 1fr
    gap: 32px

  .faq-aside
    position: static

  .faq-title
    font-size: 30px

  .faq-intro
    max-width: 640px

  .faq-header
    grid-template-columns: 108px minmax(0, 1fr)
    gap: 18px
    padding: 20px 0

  .faq-question
    font-size: 19px

  .faq-answer
    font-size: 19px
    padding: 0 0 26px 126px

@media (max-width: 599px)
  .swap-faq
    margin-top: 72px

  .faq-title
    font-size: 27px

  .faq-intro
    font-size: 17px

  .faq-header
    grid-template-columns: 1fr
    gap: 8px
    padding: 18px 0

  .faq-question
    font-size: 18px

  .faq-answer
    font-size: 18px
    padding: 0 0 22px 0

  .faq-category
    white-space: normal
</style>
