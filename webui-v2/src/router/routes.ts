import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      { path: '', component: () => import('pages/IndexPage.vue') },
      { path: 'swap', component: () => import('pages/SwapPage.vue') },
      { path: 'tokens', component: () => import('pages/TokensPage.vue') },
      { path: 'liquidity', component: () => import('pages/LiquidityPage.vue') },
      { path: 'trending', component: () => import('pages/TrendingPage.vue') }
    ],
  },

  // Always leave this as last one,
  // but you can also remove it
  {
    path: '/:catchAll(.*)*',
    component: () => import('pages/ErrorNotFound.vue'),
  },
]

export default routes
