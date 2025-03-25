export type Balances = Record<
  string,
  {
    chainBalance: string
    ownerBalances: Record<string, string>
  }
>

export const accountOwner = (owner: string) => {
  return `User:${owner}`
}

export const ownerBalance = (
  balances: Balances,
  chainId: string,
  owner: string
) => {
  return balances[chainId]?.ownerBalances[accountOwner(owner)] || '0.'
}

export const chainBalance = (balances: Balances, chainId: string) => {
  return balances[chainId]?.chainBalance || '0.'
}
