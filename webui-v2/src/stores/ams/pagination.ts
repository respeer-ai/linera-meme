export const APPLICATION_CREATED_AT_OVERLAP_MS = 1

export interface ApplicationCreatedAtRow {
  createdAt: number
}

export const resolveApplicationsQueryCreatedAfter = (createdAfter?: number) => {
  if (createdAfter === undefined) return undefined
  return Math.max(0, createdAfter - APPLICATION_CREATED_AT_OVERLAP_MS)
}

export const resolveNextApplicationsCursor = (
  previousCreatedAfter: number | undefined,
  rows: ApplicationCreatedAtRow[],
) => {
  if (!rows.length) return undefined

  const nextCreatedAfter = Math.max(...rows.map((row) => row.createdAt))
  if (previousCreatedAfter !== undefined && nextCreatedAfter <= previousCreatedAfter) {
    return undefined
  }
  return nextCreatedAfter
}
