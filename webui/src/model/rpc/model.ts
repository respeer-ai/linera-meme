export type Balances = Record<
  string,
  {
    chainBalance: number
    ownerBalances: Record<string, number>
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
  return balances[chainId].ownerBalances[accountOwner(owner)] || 0
}

export const chainBalance = (
  balances: Balances,
  chainId: string
) => {
  return balances[chainId].chainBalance
}
