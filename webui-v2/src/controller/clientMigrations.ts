import { dbKline } from './db'
import { type dbModel } from 'src/model'

export type ClientMigrationDatabase = {
  klinePoints: {
    clear: () => Promise<void>
  }
  transactions: {
    clear: () => Promise<void>
  }
  clientMigrations: {
    get: (id: string) => Promise<dbModel.ClientMigrationRecord | undefined>
    put: (record: dbModel.ClientMigrationRecord) => Promise<string>
  }
}

export type ClientMigration = {
  id: string
  description: string
  run: (db: ClientMigrationDatabase) => Promise<void>
}

export const DEFAULT_CLIENT_MIGRATIONS: ClientMigration[] = [
  {
    id: '2026-04-16-kline-cache-rebuild-v1',
    description: 'Rebuild cached K-line history after the startup/history merge bug',
    run: async (db) => {
      await db.klinePoints.clear()
    },
  },
]

export const runClientMigrations = async (
  db: ClientMigrationDatabase = dbKline,
  migrations: ClientMigration[] = DEFAULT_CLIENT_MIGRATIONS,
): Promise<void> => {
  for (const migration of migrations) {
    const existing = await db.clientMigrations.get(migration.id)
    if (existing) continue

    console.info('[ClientMigration] applying', migration.id, migration.description)
    await migration.run(db)
    await db.clientMigrations.put({
      id: migration.id,
      appliedAt: new Date().toISOString(),
    })
    console.info('[ClientMigration] applied', migration.id)
  }
}

let pendingClientMigrationRun: Promise<void> | null = null

export const ensureClientMigrations = async (): Promise<void> => {
  if (pendingClientMigrationRun) return pendingClientMigrationRun

  pendingClientMigrationRun = runClientMigrations().finally(() => {
    pendingClientMigrationRun = null
  })

  return pendingClientMigrationRun
}
