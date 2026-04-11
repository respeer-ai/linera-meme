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
            title: 'MicroMeme | Linera Meme Swap for Minable Meme and Microchain Meme Trading',
            description:
              'MicroMeme is a Linera Meme Swap for discovering, trending, and trading minable meme and microchain meme tokens on Linera.',
            path: '/',
            keywords: [
              'MicroMeme',
              'Linera Meme',
              'Linera Meme Swap',
              'Linera meme token trading',
              'Minable Meme',
              'Microchain Meme',
            ],
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
            title: 'Explore Linera Meme Tokens | MicroMeme',
            description:
              'Explore Linera meme tokens, liquidity pools, and microchain market activity on MicroMeme, a Linera Meme trading app.',
            path: '/explore',
            keywords: [
              'MicroMeme',
              'Linera Meme',
              'Linera Meme tokens',
              'Linera meme token trading',
              'Microchain Meme',
            ],
          },
        },
      },
      {
        path: 'positions',
        component: () => import('pages/PositionsPage.vue'),
        meta: {
          NeedLogined: false,
          seo: {
            title: 'Positions | MicroMeme',
            description:
              'Review liquidity positions, unclaimed fees, and reward exposure across meme pools on MicroMeme.',
            path: '/positions',
            keywords: [
              'MicroMeme',
              'Positions',
              'Liquidity positions',
              'Unclaimed fees',
              'Rewards',
            ],
          },
        },
      },
      {
        path: 'trending',
        component: () => import('pages/TrendingPage.vue'),
        meta: {
          NeedLogined: false,
          seo: {
            title: 'Trending Linera Meme Tokens | MicroMeme',
            description:
              'Track trending Linera meme tokens, volume leaders, minable meme launches, and microchain meme activity on MicroMeme.',
            path: '/trending',
            keywords: [
              'MicroMeme',
              'Linera Meme',
              'Linera Meme Swap',
              'Minable Meme',
              'Microchain Meme',
            ],
          },
        },
      },
      {
        path: 'pools/add-liquidity',
        component: () => import('pages/AddLiquidityPage.vue'),
        meta: {
          NeedLogined: false,
        },
      },
      {
        path: 'pools/remove-liquidity',
        component: () => import('pages/RemoveLiquidityPage.vue'),
        meta: {
          NeedLogined: false,
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
