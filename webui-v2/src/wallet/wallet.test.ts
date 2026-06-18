import { describe, expect, test } from 'bun:test'
import { createPinia, setActivePinia } from 'pinia'
import { constants } from 'src/constant'

describe('Wallet claim helpers', () => {
  test('maps native claim tokens to the pool ABI null token boundary', async () => {
    setActivePinia(createPinia())
    const { Wallet } = await import('./wallet')

    expect(Wallet.claimTokenVariable(constants.LINERA_NATIVE_ID)).toBe(undefined)
    expect(Wallet.claimTokenVariable('native')).toBe(undefined)
    expect(Wallet.claimTokenVariable(undefined)).toBe(undefined)
  })

  test('keeps fungible application ids as claim token variables', async () => {
    setActivePinia(createPinia())
    const { Wallet } = await import('./wallet')

    expect(Wallet.claimTokenVariable('meme-application-id')).toBe('meme-application-id')
  })
  test('rejects claim when wallet connection type is not an executable wallet', async () => {
    setActivePinia(createPinia())
    const { Wallet } = await import('./wallet')

    try {
      await Wallet._claim({ poolApplication: 'pool-app' } as never, constants.LINERA_NATIVE_ID, '1')
      throw new Error('Expected claim to reject')
    } catch (e) {
      expect(String(e).includes('Unsupported wallet type for claim')).toBe(true)
    }
  })
})
