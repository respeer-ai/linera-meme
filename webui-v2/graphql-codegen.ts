/* eslint-disable object-shorthand */
import { CodegenConfig } from '@graphql-codegen/cli';
import { constants } from './src/constant';

const config: CodegenConfig = {
  overwrite: true,
  generates: {
    './src/__generated__/graphql/service/': {
      schema: constants.formalizeSchema(constants.RPC_URL),
      documents: ['src/graphql/service.ts'],
      preset: 'client',
      plugins: [],
    },
    './src/__generated__/graphql/swap/': {
      schema: constants.formalizeSchema(constants.APPLICATION_URLS.SWAP),
      documents: ['src/graphql/swap.ts'],
      preset: 'client',
      plugins: [],
    },
    './src/__generated__/graphql/ams/': {
      schema: constants.formalizeSchema(constants.APPLICATION_URLS.AMS),
      documents: ['src/graphql/ams.ts'],
      preset: 'client',
      plugins: [],
    },
    './src/__generated__/graphql/proxy/': {
      schema: constants.formalizeSchema(constants.APPLICATION_URLS.PROXY),
      documents: ['src/graphql/proxy.ts'],
      preset: 'client',
      plugins: [],
    },
    './src/__generated__/graphql/blob/': {
      schema: constants.formalizeSchema(constants.APPLICATION_URLS.BLOB_GATEWAY),
      documents: ['src/graphql/blob.ts'],
      preset: 'client',
      plugins: [],
    },
  },
};

export default config;
