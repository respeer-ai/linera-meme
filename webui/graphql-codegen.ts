/* eslint-disable object-shorthand */
import { CodegenConfig } from '@graphql-codegen/cli'

const config: CodegenConfig = {
  overwrite: true,
  generates: {
    './src/__generated__/graphql/service/': {
      schema: 'http://api.rpc.respeer.ai/api/rpc',
      documents: ['src/graphql/service.ts'],
      preset: 'client',
      plugins: []
    },
    './src/__generated__/graphql/swap/': {
      schema: 'http://api.lineraswap.fun/api/swap/chains/dc15445f3926dbe7d56f748262a2565aec538081935c6fb7fddbb6532f7d8b05/applications/3865c36ceac24d06196383f3645cc6091f34724f91988fb31d060f25cfd6f11a',
      documents: ['src/graphql/swap.ts'],
      preset: 'client',
      plugins: []
    },
    './src/__generated__/graphql/ams/': {
      schema: 'http://api.ams.respeer.ai/api/ams/chains/042eaa8162f43e4dcf5346603e86016ee719d224f9f1df37fbfd70fb6cb70d7a/applications/bd5f3b4246e504ebc01c1f8ea0f964d1c114bbde4b00a29c3bc6949bf652aecc',
      documents: ['src/graphql/ams.ts'],
      preset: 'client',
      plugins: []
    },
    './src/__generated__/graphql/proxy/': {
      schema: 'http://api.linerameme.fun/api/proxy/chains/8994c94fb94a84d59f31280923b70cf8bca320a46c6af8f96529f0a837d1f9a1/applications/edcb213fe61101e92e640937a416797846ab9db232887af8a8b946011e0d9515',
      documents: ['src/graphql/proxy.ts'],
      preset: 'client',
      plugins: []
    }
  }
}

export default config
