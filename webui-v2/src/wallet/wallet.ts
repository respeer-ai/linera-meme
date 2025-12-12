import { account, type ams, swap, user } from 'src/stores/export';
import { CheCko } from './checko';
import { LineraWebClient } from './linera_web_client';
import { constants } from 'src/constant';

export class Wallet {
  static installed = () => {
    return window.linera || window.ethereum;
  };

  static waitOnReady = <T extends unknown[]>(f: (...args: T) => void, ...args: T) => {
    if (!window.linera && !window.ethereum) {
      return setTimeout(() => Wallet.waitOnReady(f, ...args), 1000);
    }
    f(...args);
  };

  static getProviderState = (error?: () => void, walletType?: user.WalletType) => {
    walletType = walletType || user.User.walletConnectedType();

    console.log(`Getting provider state: ${walletType} ...`);

    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.getProviderState(() => {}, error);
      case user.WalletType.Metamask:
        return LineraWebClient.getProviderState(() => {}, error);
    }
  };

  static getBalance = () => {
    const walletType = user.User.walletConnectedType();

    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.getBalance();
      case user.WalletType.Metamask:
        return LineraWebClient.getBalance();
    }
  };

  static connect = async (
    walletType: user.WalletType,
    success?: () => void,
    error?: (e: string) => void,
  ) => {
    switch (walletType) {
      case user.WalletType.CheCko:
        return await CheCko.connect(success, error);
      case user.WalletType.Metamask:
        return await LineraWebClient.connect(success, error);
    }
  };

  static subscribe = (
    onSubscribed: (subscriptionId: string) => void,
    onData: (walletType: user.WalletType, msg: unknown) => void,
  ) => {
    const walletType = user.User.walletConnectedType();

    switch (walletType) {
      case user.WalletType.CheCko:
        return CheCko.subscribe(onSubscribed, onData);
      case user.WalletType.Metamask:
        return LineraWebClient.subscribe(onData);
    }
  };

  static unsubscribe = (subscriptionId: string) => {
    CheCko.unsubscribe(subscriptionId);
  };

  static _swap = async (sellToken: ams.Application, buyToken: ams.Application, amount: string) => {
    const pools = swap.Swap.pools();
    const sellTokenId = sellToken?.applicationId || constants.LINERA_NATIVE_ID;
    const buyTokenId = buyToken?.applicationId || constants.LINERA_NATIVE_ID;

    const pool = pools.find((el) => {
      return (
        (el.token0 === buyTokenId && el.token1 === sellTokenId) ||
        (el.token1 === buyTokenId && el.token0 === sellTokenId)
      );
    });
    if (!pool) {
      throw new Error('Invalid pool');
    }

    const variables = {
      amount0In: sellTokenId === pool.token0 ? amount : undefined,
      amount1In: sellTokenId === pool.token1 ? amount : undefined,
      amount0OutMin: undefined,
      amount1OutMin: undefined,
      to: undefined,
      blockTimestamp: undefined,
    };

    const walletType = user.User.walletConnectedType();
    const poolApplicationId = account._Account.accountApplication(
      pool.poolApplication as account.Account,
    ) as string;

    switch (walletType) {
      case user.WalletType.CheCko:
        return await CheCko.swap(poolApplicationId, variables);
      case user.WalletType.Metamask:
        return await LineraWebClient.swap(poolApplicationId, variables);
    }
  };

  static swap = async (
    sellToken: ams.Application,
    buyToken: ams.Application,
    amount: string,
    done?: () => void,
    error?: (e: string) => void,
  ) => {
    try {
      await Wallet._swap(sellToken, buyToken, amount);
      done?.();
    } catch (e) {
      error?.(JSON.stringify(e));
    }
  };
}
