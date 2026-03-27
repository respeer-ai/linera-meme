import { useMeta } from 'quasar'

const fallbackSiteUrl = 'https://testnet-conway.linerameme.fun'
const siteName = 'Linera Meme'
const defaultKeywords = [
  'Linera Meme',
  'Linera Meme Swap',
  'Linera DEX',
  'Linera token',
  'Linera mining',
  'Linera microchain',
  'Linera realtime trading',
]

export interface SeoInput {
  title: string
  description: string
  path: string
  keywords?: string[]
}

type SeoSource = SeoInput | (() => SeoInput)

const siteUrl = () => import.meta.env.VITE_SITE_URL || fallbackSiteUrl

const absoluteUrl = (path: string) => new URL(path, siteUrl()).toString()

const normalizeDescription = (description: string) => description.trim().replace(/\s+/g, ' ')

const jsonLd = (input: SeoInput) => {
  const canonicalUrl = absoluteUrl(input.path)
  const description = normalizeDescription(input.description)
  return JSON.stringify([
    {
      '@context': 'https://schema.org',
      '@type': 'WebSite',
      name: siteName,
      url: siteUrl(),
      description,
      potentialAction: {
        '@type': 'SearchAction',
        target: `${siteUrl()}/explore`,
        'query-input': 'required name=search_term_string',
      },
    },
    {
      '@context': 'https://schema.org',
      '@type': 'WebPage',
      name: input.title,
      url: canonicalUrl,
      description,
      isPartOf: {
        '@type': 'WebSite',
        name: siteName,
        url: siteUrl(),
      },
      about: [...new Set(input.keywords || defaultKeywords)],
    },
  ])
}

const resolveSeoInput = (input: SeoSource) => (typeof input === 'function' ? input() : input)

export const usePageSeo = (input: SeoSource) => {
  useMeta(() => {
    const seo = resolveSeoInput(input)
    const description = normalizeDescription(seo.description)
    const canonicalUrl = absoluteUrl(seo.path)
    const keywords = [...new Set([...(seo.keywords || []), ...defaultKeywords])].join(', ')

    return {
      title: seo.title,
      meta: {
        description: {
          name: 'description',
          content: description,
        },
        keywords: {
          name: 'keywords',
          content: keywords,
        },
        robots: {
          name: 'robots',
          content: 'index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1',
        },
        ogType: {
          property: 'og:type',
          content: 'website',
        },
        ogSiteName: {
          property: 'og:site_name',
          content: siteName,
        },
        ogTitle: {
          property: 'og:title',
          content: seo.title,
        },
        ogDescription: {
          property: 'og:description',
          content: description,
        },
        ogUrl: {
          property: 'og:url',
          content: canonicalUrl,
        },
        ogImage: {
          property: 'og:image',
          content: absoluteUrl('/favicon.png'),
        },
        twitterCard: {
          name: 'twitter:card',
          content: 'summary',
        },
        twitterTitle: {
          name: 'twitter:title',
          content: seo.title,
        },
        twitterDescription: {
          name: 'twitter:description',
          content: description,
        },
        twitterImage: {
          name: 'twitter:image',
          content: absoluteUrl('/favicon.png'),
        },
      },
      link: {
        canonical: {
          rel: 'canonical',
          href: canonicalUrl,
        },
      },
      script: {
        structuredData: {
          type: 'application/ld+json',
          innerHTML: jsonLd({
            ...seo,
            description,
          }),
        },
      },
    }
  })
}

export const seoSiteUrl = siteUrl
