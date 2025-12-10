import { defineStore } from '#q-app/wrappers';
import { createPinia } from 'pinia';

/*
 * When adding new properties to stores, you should also
 * extend the `PiniaCustomProperties` interface.
 * @see https://pinia.vuejs.org/core-concepts/plugins.html#typing-new-store-properties
 */
declare module 'pinia' {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type
  export interface PiniaCustomProperties {
    // add your custom properties here, if any
  }
}

/*
 * If not building with SSR mode, you can
 * directly export the Store instantiation;
 *
 * The function below can be async too; either use
 * async/await or return a Promise which resolves
 * with the Store instance.
 */

export default defineStore((/* { ssrContext } */) => {
  const pinia = createPinia();

  // You can add Pinia plugins here
  // pinia.use(SomePiniaPlugin)

  return pinia;
});

export * as notify from './notify'
export * as user from './user'
export * as request from './request'
export * as ams from './ams'
export * as proxy from './proxy'
export * as kline from './kline'
export * as store from './store'
export * as blob from './blob'
export * as meme from './meme'
export * as account from './account'
export * as swap from './swap'
export * as block from './block'
export * as transaction from './transaction'
export * as pool from './pool'
