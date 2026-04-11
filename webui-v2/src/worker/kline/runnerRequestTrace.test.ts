import { describe, expect, test } from 'bun:test'
import { Interval } from 'src/stores/kline/const'
import { appendKlineTraceParams, buildKlineRequestTraceId } from './runner'

describe('buildKlineRequestTraceId', () => {
  test('encodes request identity and window bounds for backend correlation', () => {
    expect(
      buildKlineRequestTraceId({
        token0: '4cfc2f42a0d6bcda3fe5d702324089de80c5885458e7d80c5a0f48d2bce916cf',
        token1: 'TLINERA',
        startAt: 1775561640000,
        endAt: 1775565240000,
        interval: Interval.ONE_MINUTE,
        reverse: false,
        requestId: 17,
      }),
    ).toBe('17:1min:forward:1775561640000:1775565240000:4cfc2f42:TLINERA')
  })

  test('appends trace metadata as query params without custom headers', () => {
    expect(
      appendKlineTraceParams(
        'https://api.testnet-conway.kline.lineraswap.fun/api/kline/points/token0/a/token1/b/start_at/1/end_at/2/interval/1min',
        '17:1min:forward:1:2:aaaaaaaa:TLINERA',
        1775565404870,
      ),
    ).toBe(
      'https://api.testnet-conway.kline.lineraswap.fun/api/kline/points/token0/a/token1/b/start_at/1/end_at/2/interval/1min?request_id=17%3A1min%3Aforward%3A1%3A2%3Aaaaaaaaa%3ATLINERA&client_sent_at_ms=1775565404870',
    )
  })
})
