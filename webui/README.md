# kline (kline)

vue3 framework use quasar ui and pinia manage store

## dev environment

node: v18.20.5

yarn: 1.22.22

npm: 10.8.2

quasar: 1.11.0

## Install the dependencies

```bash
yarn
```

## Start the app in development mode (hot-code reloading, error reporting, etc.)

```bash
quasar dev
```

## Lint the files

```bash
yarn lint
```

## Build the app for production

```bash
quasar build
```

## All compile steps

```bash
yarn #install the dependencies
yarn build #build the product,output folder: project/dist/spa
```

Deploy the frontend using nginx

## compatible babel

> yarn add @babel/preset-env babel-jest @babel/core --dev

## practice of unit test link

- [Vue Test Utils](https://test-utils.vuejs.org/guide/)
- [Pinia Test](https://pinia.vuejs.org/cookbook/testing.html)
- [Pinia Test Example](https://github.com/vuejs/pinia/blob/v2/packages/testing/src/testing.spec.ts)
- [Quasar Test Example](https://github.com/quasarframework/quasar-testing/blob/dev/packages/unit-jest/src/templates/typescript/test/jest/___tests__/MyButton.spec.ts)

## Customize the configuration

See [Configuring quasar.conf.js](https://quasar.dev/quasar-cli/quasar-conf-js).
