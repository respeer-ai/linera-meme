import type { KLineData } from './chart/KlineData'

export type KlineSnapshotKeyInput = {
  token0: string | undefined
  token1: string | undefined
  poolId: number | undefined
  poolApplication: string | undefined
  interval: string
}

export const buildKlineSnapshotKey = ({
  token0,
  token1,
  poolId,
  poolApplication,
  interval,
}: KlineSnapshotKeyInput): string | null => {
  if (!token0 || !token1 || poolId === undefined || !poolApplication) return null
  return [token0, token1, poolId, poolApplication, interval].join('|')
}

export const cloneKlineSnapshot = (points: KLineData[]): KLineData[] =>
  points.map((point) => ({ ...point }))
