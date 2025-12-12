export type Balances = Record<
  string,
  {
    chainBalance: string;
    ownerBalances: Record<string, string>;
  }
>;

export const ownerBalance = (balances: Balances, chainId: string, owner: string) => {
  return balances[chainId]?.ownerBalances[owner] || '0.';
};

export const chainBalance = (balances: Balances, chainId: string) => {
  return balances[chainId]?.chainBalance || '0.';
};
