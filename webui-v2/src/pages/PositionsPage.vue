<template>
  <q-page class='row justify-center'>
    <main class='page-width positions-page'>
      <section class='main-column'>
        <div class='reward-card'>
          <div class='reward-copy'>
            <div class='reward-value'>
              0 LMM
              <q-img class='reward-inline-logo' :src='constants.MICROMEME_LOGO' width='18px' height='18px' fit='contain' />
            </div>
            <div class='reward-label'>
              Rewards earned
              <span class='reward-info'>i
                <q-tooltip class='reward-tooltip' anchor='top middle' self='bottom middle'>
                  <p>LMM represents your liquidity share, not a tradable token.</p>
                  <p>You can only use it to redeem liquidity and earn trading fees.</p>
                </q-tooltip>
              </span>
            </div>
            <div class='reward-link'>Find pools with LMM rewards -></div>
            <div class='reward-caption'>
              Eligible pools have token rewards so you can earn more
            </div>
          </div>
          <div class='reward-side'>
          <q-btn
            flat
            no-caps
            rounded
            class='reward-action'
            label='Collect rewards'
          />
          </div>
        </div>

        <section class='positions-section'>
          <h1 class='positions-title q-ma-none'>Your positions</h1>

          <div class='filter-row'>
            <button class='filter-btn filter-btn-primary'>
              <span class='filter-plus'>+</span>
              <span>New</span>
            </button>
            <button class='filter-btn'>
              <span>Status</span>
              <span class='filter-caret'>⌄</span>
            </button>
          </div>

          <div class='empty-card'>
            <div class='empty-icon-wrap'>
              <div class='empty-icon'>≈</div>
            </div>
            <div class='empty-title'>No positions</div>
            <div class='empty-text'>
              You don't have any liquidity positions. Create a new
              position to start earning fees and rewards on eligible pools.
            </div>
            <div class='empty-actions'>
              <button class='empty-btn empty-btn-secondary'>Explore pools</button>
              <button class='empty-btn empty-btn-primary'>New position</button>
            </div>
          </div>

          <div class='notice-row'>
            <div class='notice-icon'>i</div>
            <div class='notice-copy'>
              <div class='notice-title'>Looking for your closed positions?</div>
              <div class='notice-text'>You can see them by using the filter at the top of the page.</div>
            </div>
            <button class='notice-close'>×</button>
          </div>

          <div class='legacy-hint'>
            Some v2 positions aren't displayed automatically.
            <a href='#' @click.prevent>Import V2 positions</a>
          </div>
        </section>
      </section>
    </main>
  </q-page>
</template>

<script setup lang='ts'>
import { useMeta } from 'quasar'
import { useRoute } from 'vue-router'
import { usePageSeo } from 'src/utils/seo'
import { constants } from 'src/constant'

const route = useRoute()

useMeta(() => ({
  script: {
    positionsStructuredData: {
      type: 'application/ld+json',
      innerHTML: JSON.stringify({
        '@context': 'https://schema.org',
        '@type': 'CollectionPage',
        name: 'MicroMeme Positions',
        description: 'Positions view for liquidity positions and rewards on MicroMeme.',
      }),
    },
  },
}))

usePageSeo(() => ({
  title: route.meta.seo?.title || 'Positions | MicroMeme',
  description:
    route.meta.seo?.description ||
    'Review your liquidity positions, unclaimed fees, and reward exposure on MicroMeme.',
  path: route.meta.seo?.path || route.path,
  keywords: route.meta.seo?.keywords || [
    'MicroMeme positions',
    'Liquidity positions',
    'Rewards',
  ],
}))
</script>

<style scoped lang='sass'>
.positions-page
  padding-top: 28px
  padding-bottom: 72px

.main-column
  width: 100%
  max-width: 760px
  margin: 0 auto

.reward-card,
.empty-card,
.notice-row
  border: 1px solid rgba(255, 255, 255, 0.08)
  background: rgba(255, 255, 255, 0.018)
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.025)

.reward-card
  display: flex
  justify-content: space-between
  align-items: flex-start
  gap: 24px
  padding: 20px
  border-radius: 24px
  background-image: radial-gradient(rgba(255, 255, 255, 0.05) 0.7px, transparent 0.7px)
  background-size: 12px 12px
  background-position: -5px -5px

.reward-copy
  min-width: 0

.reward-value
  font-size: 50px
  line-height: 1
  letter-spacing: -0.05em
  font-weight: 500
  color: var(--q-light)

.reward-side
  display: flex
  flex-direction: column
  align-items: flex-end
  justify-content: flex-start

.reward-inline-logo
  display: inline-block
  width: 1em !important
  height: 1em !important
  margin-left: 6px
  vertical-align: 0.02em

.reward-label
  margin-top: 8px
  font-size: 14px
  font-weight: 600
  color: #9aa0ab

.reward-info
  display: inline-flex
  align-items: center
  justify-content: center
  width: 16px
  height: 16px
  margin-left: 6px
  border-radius: 999px
  border: 1px solid rgba(255, 255, 255, 0.1)
  background: rgba(255, 255, 255, 0.04)
  color: #aab1bd
  font-size: 10px
  font-weight: 600
  vertical-align: middle

:global(.reward-tooltip.q-tooltip)
  max-width: 420px
  padding: 12px 14px !important
  color: #d7dde7 !important
  background: rgba(16, 18, 24, 0.96) !important
  border: 1px solid rgba(255, 255, 255, 0.1) !important
  border-radius: 14px !important
  box-shadow: none !important
  font-size: 14px
  line-height: 1.4
  white-space: normal !important
  display: block

:global(.reward-tooltip.q-tooltip p)
  margin: 0

:global(.reward-tooltip.q-tooltip p + p)
  margin-top: 5px

.reward-link
  margin-top: 28px
  font-size: 14px
  font-weight: 700
  color: var(--q-light)

.reward-caption
  margin-top: 4px
  font-size: 14px
  color: #9aa0ab

.reward-action
  min-height: 34px
  padding: 0 14px
  border-radius: 14px
  border: 1px solid rgba(255, 255, 255, 0.1)
  color: var(--q-light)
  background: rgba(255, 255, 255, 0.02)

.positions-section
  margin-top: 34px

.positions-title
  font-size: 22px
  line-height: 1.1
  font-weight: 700
  color: var(--q-light)

.filter-row
  display: flex
  flex-wrap: wrap
  gap: 8px
  margin-top: 16px

.filter-btn,
.empty-btn,
.notice-close
  border: 0
  background: transparent
  color: inherit
  font: inherit
  cursor: pointer

.filter-btn
  display: inline-flex
  align-items: center
  gap: 8px
  height: 38px
  padding: 0 14px
  border-radius: 18px
  background: rgba(255, 255, 255, 0.06)
  color: var(--q-light)
  font-size: 14px
  font-weight: 700
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03)

.filter-btn-primary
  background: #f5f5f7
  color: #111

.filter-plus
  font-size: 16px
  line-height: 1

.filter-caret
  font-size: 12px
  opacity: 0.75

.filter-btn-icon
  min-width: 60px

.empty-card
  display: flex
  flex-direction: column
  align-items: center
  justify-content: center
  min-height: 198px
  margin-top: 20px
  padding: 28px 24px
  border-radius: 18px
  text-align: center

.empty-icon-wrap
  display: flex
  align-items: center
  justify-content: center
  width: 42px
  height: 42px
  border-radius: 12px
  background: rgba(255, 255, 255, 0.07)

.empty-icon
  color: #d8d8d8
  font-size: 22px
  line-height: 1

.empty-title
  margin-top: 18px
  font-size: 16px
  font-weight: 700
  color: var(--q-light)

.empty-text
  max-width: 440px
  margin-top: 10px
  font-size: 14px
  line-height: 1.55
  color: #9aa0ab

.empty-actions
  display: flex
  gap: 10px
  margin-top: 18px

.empty-btn
  min-width: 128px
  height: 36px
  padding: 0 18px
  border-radius: 14px
  font-size: 14px
  font-weight: 700

.empty-btn-secondary
  background: rgba(255, 255, 255, 0.08)
  color: var(--q-light)

.empty-btn-primary
  background: #f5f5f7
  color: #111

.notice-row
  display: flex
  align-items: flex-start
  gap: 12px
  margin-top: 18px
  padding: 14px 16px
  border-radius: 14px

.notice-icon
  display: flex
  align-items: center
  justify-content: center
  width: 18px
  height: 18px
  margin-top: 2px
  border-radius: 999px
  background: rgba(255, 255, 255, 0.08)
  font-size: 12px
  font-weight: 700
  color: var(--q-light)

.notice-copy
  min-width: 0
  flex: 1 1 auto

.notice-title
  font-size: 14px
  font-weight: 700
  color: var(--q-light)

.notice-text
  margin-top: 2px
  font-size: 13px
  color: #9aa0ab

.notice-close
  font-size: 22px
  line-height: 1
  color: var(--q-neutral)

.legacy-hint
  margin-top: 38px
  text-align: center
  font-size: 14px
  color: #9aa0ab

  a
    margin-left: 4px
    color: var(--q-light)
    text-decoration: none

@media (max-width: 720px)
  .positions-page
    padding-top: 18px

  .reward-card,
  .empty-card,
  .notice-row
    padding-left: 16px
    padding-right: 16px

  .reward-card
    display: block

  .reward-action
    margin-top: 18px

  .empty-actions
    flex-direction: column
    width: 100%

  .empty-btn
    width: 100%
</style>
