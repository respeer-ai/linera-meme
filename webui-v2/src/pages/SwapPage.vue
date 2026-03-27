<template>
  <q-page class='row justify-center'>
    <main class='page-width' aria-label='Linera Meme Swap trading page'>
      <div class='q-my-xl' role='region' aria-label='Meme token swap interface'>
        <trade-view />
      </div>
      <section class='swap-faq q-mb-xl' aria-labelledby='swap-faq-title' aria-describedby='swap-faq-intro'>
        <div class='faq-kicker text-primary text-weight-medium'>About Linera Meme Swap</div>
        <h2 id='swap-faq-title' class='faq-title q-mt-sm q-mb-sm'>Trading FAQ</h2>
        <p id='swap-faq-intro' class='q-ma-none text-neutral faq-intro'>
          A concise guide to Linera, microchains, meme mining, and realtime token activity on the swap page.
        </p>
        <div class='q-mt-lg'>
          <q-expansion-item
            v-for='item in faqItems'
            :key='item.question'
            class='faq-row'
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
    </main>
  </q-page>
</template>

<script setup lang='ts'>
import { useMeta } from 'quasar'
import { useRoute } from 'vue-router'
import TradeView from 'src/components/trade/TradeView.vue'
import { usePageSeo } from 'src/utils/seo'

const route = useRoute()
const faqItems = [
  {
    question: 'What Is Linera and Why Does It Matter for Linera Meme Swap?',
    answer:
      'Linera is a protocol built for real-time Web3 applications. Linera Meme Swap uses that foundation to support responsive market updates, token trading flows, and application-specific interactions designed for active meme markets.',
  },
  {
    question: 'What Is Linera Meme Swap?',
    answer:
      'Linera Meme Swap is the main trading interface for meme tokens in this product. It combines token discovery, live pricing, charting, swap execution, and mining-related participation into one Linera-native experience.',
  },
  {
    question: 'How Do Linera Microchains Improve Meme Token Trading?',
    answer:
      'Linera microchains are designed to handle activity in parallel and support responsive applications. For a meme trading interface, that helps create a smoother flow for market updates, token state changes, and real-time interaction across the app.',
  },
  {
    question: 'What Is Meme Mining on Linera Meme Swap?',
    answer:
      'Meme Mining refers to reward or incentive mechanisms around a meme token ecosystem. Depending on the token design, that can include mining supply, liquidity participation, trading activity, or other reward logic defined by the project.',
  },
  {
    question: 'Can I Create My Own Meme Token on Linera Meme Swap?',
    answer:
      'Yes. The current product includes a Create Meme flow. If your wallet type and environment support it, you can configure token details such as name, ticker, supply, description, liquidity settings, and optional mining parameters.',
  },
  {
    question: 'How Can I Earn Income From Meme Tokens?',
    answer:
      'Income may come from several sources, including price appreciation, active trading, liquidity provision, or participation in mining and reward programs. The exact outcome depends on market conditions and on the rules of each meme token or pool.',
  },
  {
    question: 'Are Meme Token Trades and Updates Real Time?',
    answer:
      'The interface is designed for a real-time experience and continuously refreshes token data, market activity, and charts. Actual completion still depends on chain execution and synchronization, but the product is built to feel fast and reactive.',
  },
  {
    question: 'How Are Swap Fees Charged on Linera Meme Swap?',
    answer:
      'The trading flow includes estimated network gas and a pool trading fee shown in the swap details. In the current interface, the trade detail view displays a 0.3% fee and also estimates network gas before you confirm execution.',
  },
  {
    question: 'How Do I Join Meme Mining?',
    answer:
      'You join Meme Mining by participating in a token or pool that enables mining-related rewards. In this product, mining is tied to token configuration and pool participation, so the exact entry path depends on whether the project has enabled mining.',
  },
  {
    question: 'Where Can I Check My Meme Mining or Trading Earnings?',
    answer:
      'You can usually track earnings through wallet balances, token positions, trading history, pool participation, and any mining or reward views exposed by the token or application. Over time, these earnings can also be surfaced in more dedicated dashboards.',
  },
]

useMeta(() => ({
  script: {
    faqStructuredData: {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'FAQPage',
        mainEntity: faqItems.map((item) => ({
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

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Linera Meme Swap - Realtime Meme Token Trading on Linera',
  description:
    route.meta.seo?.description ||
    'Trade meme tokens on Linera with realtime pricing, microchain-based execution, live charts, and low-latency swap flows.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'Linera Meme',
    'Linera Meme Swap',
    'Linera DEX',
    'Linera token',
    'Linera realtime',
  ],
}))
</script>

<style scoped lang='sass'>
.faq-kicker
  letter-spacing: 0.12em
  text-transform: uppercase
  font-size: 15px

.faq-title
  font-size: 34px
  line-height: 1.1
  letter-spacing: -0.03em
  font-weight: 500

.faq-intro
  max-width: 720px
  line-height: 1.8
  font-size: 22px

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
  letter-spacing: -0.01em
  padding-right: 8px
  flex: 1 1 auto
  min-width: 0
  white-space: nowrap
  word-break: normal

.faq-answer
  line-height: 1.85
  padding: 0 8px 24px 0
  font-size: 21px
  max-width: none
  width: 100%

::v-deep(.swap-faq .q-expansion-item__toggle-icon)
  font-size: 32px

::v-deep(.swap-faq .q-item)
  min-height: auto
  padding-left: 0
  padding-right: 0
  align-items: center

::v-deep(.swap-faq .q-item__section)
  min-width: 0
  flex: 1 1 auto

::v-deep(.swap-faq .q-item__section--side)
  align-self: center
  flex: 0 0 auto
  padding-left: 6px

::v-deep(.swap-faq .q-focus-helper)
  display: none

::v-deep(.swap-faq .q-expansion-item__container)
  transition: opacity 0.2s ease

@media (max-width: 1023px)
  .faq-title
    font-size: 30px

  .faq-question
    font-size: 19px
    white-space: normal

  .faq-answer
    font-size: 19px
    padding-right: 0

  .faq-intro
    max-width: none
    font-size: 20px

@media (max-width: 599px)
  .faq-title
    font-size: 27px

  .faq-question
    font-size: 18px
    white-space: normal

  .faq-intro
    font-size: 18px

  .faq-answer
    font-size: 18px
    padding-bottom: 20px
</style>
