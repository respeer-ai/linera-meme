export default {
  common: {
    failed: 'Action failed',
    success: 'Action was successful',
  },
  navigation: {
    swap: 'Swap',
    explore: 'Explore',
    positions: 'Positions',
    trending: 'Trending',
    docs: 'Docs',
  },
  header: {
    theme: 'Theme',
    language: 'Language',
  },
  language: {
    english: 'English',
    traditionalChinese: 'Traditional Chinese',
    current: 'Current language',
  },
  faq: {
    title: 'FAQ',
    intro:
      'Core product and protocol questions for trading meme tokens, creating pools, launching tokens, and understanding settlement on Linera.',
    topics: ['Trading', 'Liquidity', 'Token launch', 'Settlement'],
    items: [
      {
        category: 'Product',
        question: 'What is MicroMeme on Linera?',
        answer:
          'MicroMeme is one Linera-native meme trading product. It combines meme token creation, AMM pool creation, token swaps, live charts, pool discovery, positions, and transaction history in a single interface for Linera applications.',
      },
      {
        category: 'Architecture',
        question: 'How does MicroMeme use Linera microchains?',
        answer:
          'MicroMeme is built around Linera applications and application-owned chains. Meme tokens, swap routing, and pools are separate on-chain applications that communicate through Linera messages, so market actions can settle across the relevant application and user chains instead of relying on a single monolithic contract.',
      },
      {
        category: 'Pricing',
        question: 'How are meme token prices calculated?',
        answer:
          'Pools use a V2-style constant product AMM model. The visible quote is based on current pool reserves, the selected input amount, and the pool trading fee; the final output can still change if the pool state moves before settlement.',
      },
      {
        category: 'Trading',
        question: 'What should I review before swapping?',
        answer:
          'Before confirming a swap, review the token pair, input and output amounts, price impact, slippage tolerance, pool fee, estimated Linera network gas, and the wallet account that will receive the result.',
      },
      {
        category: 'Data freshness',
        question: 'Why do charts, balances, and transactions update after settlement?',
        answer:
          'The WebUI is event driven. It refreshes market data after chain events are ingested, decoded, projected, and pushed into the frontend stores. Wallet approval is only the start of the flow; visible state becomes fresh after the related pool, transaction, and market projections catch up.',
      },
      {
        category: 'Token launch',
        question: 'How do I create a meme token?',
        answer:
          'The Create Meme flow lets a supported wallet configure name, ticker, logo, description, initial supply, decimals, social links, optional mining settings, and initial liquidity parameters. When initial liquidity is enabled, the token launch can create its first native-token pool as part of the launch flow.',
      },
      {
        category: 'Bootstrap',
        question: 'What is virtual initial liquidity?',
        answer:
          'Virtual initial liquidity is a launch-time pool parameter used by meme initialization semantics. It affects pricing and pool-share math for that bootstrap path, but it is not a claimable user balance and cannot be withdrawn as ordinary liquidity.',
      },
      {
        category: 'Positions',
        question: 'What does LMM mean in positions?',
        answer:
          'LMM is the liquidity share minted by a MicroMeme pool. It represents a provider\'s share of a V2-style pool, not a separate tradeable meme token. Active and closed positions are derived from recorded add-liquidity and remove-liquidity transactions.',
      },
      {
        category: 'Funds',
        question: 'Why might funds appear as claimable balances?',
        answer:
          'Some cross-application outcomes, such as swap outputs, remove-liquidity payouts, refunds, or protocol-fee withdrawals, are represented as claimable balances when direct delivery should not be assumed. This keeps recoverable value explicit instead of hiding it behind an unreliable push transfer.',
      },
      {
        category: 'Risk',
        question: 'Does MicroMeme guarantee profit, rewards, or successful execution?',
        answer:
          'No. Meme tokens and liquidity positions can be volatile and may involve slippage, changing pool exposure, project-specific mining rules, failed wallet approvals, or delayed cross-chain settlement. Always inspect the transaction details before signing.',
      },
    ],
  },
  transactions: {
    columns: {
      time: 'Time',
      swap: 'Swap',
      value: 'Value',
      bought: 'Bought',
      sold: 'Sold',
      address: 'Address',
    },
    action: {
      swap: 'Swap',
      for: 'for',
    },
    empty: {
      title: 'No transactions',
      caption: 'Transactions will appear here after swaps settle.',
    },
  },
}
