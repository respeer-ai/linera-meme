import { describe, expect, test } from 'bun:test'

import { runClientMigrations, type ClientMigration, type ClientMigrationDatabase } from './clientMigrations'

const createFakeDb = (appliedIds: string[] = []): ClientMigrationDatabase & {
  clearedTables: string[]
  appliedOrder: string[]
} => {
  const records = new Map(
    appliedIds.map((id) => [
      id,
      {
        id,
        appliedAt: '2026-04-16T00:00:00.000Z',
      },
    ]),
  )

  const clearedTables: string[] = []
  const appliedOrder: string[] = []

  return {
    clearedTables,
    appliedOrder,
    klinePoints: {
      clear: () => {
        clearedTables.push('klinePoints')
        return Promise.resolve()
      },
    },
    transactions: {
      clear: () => {
        clearedTables.push('transactions')
        return Promise.resolve()
      },
    },
    clientMigrations: {
      get: (id: string) => Promise.resolve(records.get(id)),
      put: (record) => {
        records.set(record.id, record)
        appliedOrder.push(record.id)
        return Promise.resolve(record.id)
      },
    },
  }
}

describe('runClientMigrations', () => {
  test('applies pending migrations in order and records completion', async () => {
    const db = createFakeDb()
    const migrations: ClientMigration[] = [
      {
        id: 'migration-a',
        description: 'clear kline',
        run: async (migrationDb) => {
          await migrationDb.klinePoints.clear()
        },
      },
      {
        id: 'migration-b',
        description: 'clear transactions',
        run: async (migrationDb) => {
          await migrationDb.transactions.clear()
        },
      },
    ]

    await runClientMigrations(db, migrations)

    expect(db.clearedTables).toEqual(['klinePoints', 'transactions'])
    expect(db.appliedOrder).toEqual(['migration-a', 'migration-b'])
  })

  test('skips migrations that were already applied', async () => {
    const db = createFakeDb(['migration-a'])
    const migrations: ClientMigration[] = [
      {
        id: 'migration-a',
        description: 'clear kline',
        run: async (migrationDb) => {
          await migrationDb.klinePoints.clear()
        },
      },
      {
        id: 'migration-b',
        description: 'clear transactions',
        run: async (migrationDb) => {
          await migrationDb.transactions.clear()
        },
      },
    ]

    await runClientMigrations(db, migrations)

    expect(db.clearedTables).toEqual(['transactions'])
    expect(db.appliedOrder).toEqual(['migration-b'])
  })

  test('supports later migrations without re-running earlier ones', async () => {
    const db = createFakeDb(['migration-a', 'migration-b'])
    const migrations: ClientMigration[] = [
      {
        id: 'migration-a',
        description: 'clear kline',
        run: async (migrationDb) => {
          await migrationDb.klinePoints.clear()
        },
      },
      {
        id: 'migration-b',
        description: 'clear transactions',
        run: async (migrationDb) => {
          await migrationDb.transactions.clear()
        },
      },
      {
        id: 'migration-c',
        description: 'clear both',
        run: async (migrationDb) => {
          await migrationDb.klinePoints.clear()
          await migrationDb.transactions.clear()
        },
      },
    ]

    await runClientMigrations(db, migrations)

    expect(db.clearedTables).toEqual(['klinePoints', 'transactions'])
    expect(db.appliedOrder).toEqual(['migration-c'])
  })
})
