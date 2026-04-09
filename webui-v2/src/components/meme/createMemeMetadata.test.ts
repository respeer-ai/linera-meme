import { describe, expect, test } from 'bun:test'

type Metadata = {
  description: string
  website?: string
  twitter?: string
  telegram?: string
  discord?: string
  github?: string
  liveStream?: string
}

const createMetadata = (): Metadata => ({
  description: 'desc',
  website: 'https://project.example',
  twitter: '@project',
  telegram: 'https://t.me/project',
  discord: 'https://discord.gg/project',
  github: 'https://github.com/project/repo',
  liveStream: 'https://youtube.com/watch?v=demo',
})

describe('Create Meme metadata mapping', () => {
  test('keeps each social and link field on its own metadata key', () => {
    const metadata = createMetadata()

    expect(metadata).toEqual({
      description: 'desc',
      website: 'https://project.example',
      twitter: '@project',
      telegram: 'https://t.me/project',
      discord: 'https://discord.gg/project',
      github: 'https://github.com/project/repo',
      liveStream: 'https://youtube.com/watch?v=demo',
    })
  })

  test('changing one field does not overwrite website or other metadata fields', () => {
    const metadata = createMetadata()
    metadata.twitter = '@project_v2'

    expect(metadata.website).toBe('https://project.example')
    expect(metadata.twitter).toBe('@project_v2')
    expect(metadata.telegram).toBe('https://t.me/project')
    expect(metadata.discord).toBe('https://discord.gg/project')
    expect(metadata.github).toBe('https://github.com/project/repo')
    expect(metadata.liveStream).toBe('https://youtube.com/watch?v=demo')
  })
})
