import type { RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: () => import('layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        component: () => import('pages/SwapPage.vue'),
        meta: {
          NeedLogined: false,
          seo: {
            title: 'Linera Meme Swap - Realtime Meme Token Trading on Linera',
            description:
              'Trade meme tokens on Linera with realtime pricing, microchain-based execution, live charts, and low-latency swap flows.',
            path: '/',
            keywords: ['Linera Meme Swap', 'Linera Swap', 'Linera DEX', 'realtime token trading'],
          },
        },
      },
      {
        path: 'swap',
        redirect: '/',
      },
      {
        path: 'explore',
        component: () => import('pages/ExplorePage.vue'),
        meta: {
          NeedLogined: false,
          seo: {
            title: 'Explore Linera Meme Tokens, Pools, and Microchain Markets',
            description:
              'Explore Linera meme tokens, liquidity pools, token stats, and microchain market activity in one realtime dashboard.',
            path: '/explore',
            keywords: ['Linera Meme tokens', 'Linera token explorer', 'Linera microchain markets'],
          },
        },
      },
      {
        path: 'trending',
        component: () => import('pages/TrendingPage.vue'),
        meta: {
          NeedLogined: false,
          seo: {
            title: 'Trending Linera Meme Tokens - Realtime Movers, Volume, and New Launches',
            description:
              'Track trending Linera meme tokens with realtime gainers, volume leaders, and new token launches across the Linera ecosystem.',
            path: '/trending',
            keywords: ['trending Linera tokens', 'Linera Meme trending', 'Linera realtime volume'],
          },
        },
      },
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
