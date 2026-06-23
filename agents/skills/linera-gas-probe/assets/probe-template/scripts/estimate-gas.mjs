import { execFileSync } from 'node:child_process'

const rpcUrl = process.env.GAS_PROBE_RPC_URL || 'http://localhost:19180'
const chainId = process.env.GAS_PROBE_CHAIN_ID
const callerApp = process.env.GAS_PROBE_CALLER_APP_ID
const calleeApp = process.env.GAS_PROBE_CALLEE_APP_ID
const opgen = process.env.GAS_PROBE_OPGEN || '.tmp-gas-probe/target/release/gas-probe-opgen'

if (!chainId || !callerApp || !calleeApp) {
  throw new Error('Set GAS_PROBE_CHAIN_ID, GAS_PROBE_CALLER_APP_ID, GAS_PROBE_CALLEE_APP_ID')
}

const payloadKinds = [
  'amount',
  'account',
  'account-amount',
  'pool-like-small',
  'bytes32',
  'bytes128',
  'bytes512',
  'bytes2048',
]

const cases = [{ name: 'noop', args: ['noop'], iterations: 1, family: 'baseline' }]
for (const kind of payloadKinds) {
  cases.push({ name: `bcs_encode_${kind}_x100`, args: ['bcs-encode', kind, '100'], iterations: 100, family: 'bcs_encode', kind })
  cases.push({ name: `bcs_decode_${kind}_x100`, args: ['bcs-decode', kind, '100'], iterations: 100, family: 'bcs_decode', kind })
}
for (const iterations of [1, 10, 100]) {
  cases.push({ name: `call_application_noop_x${iterations}`, args: ['call-noop', calleeApp, String(iterations)], iterations, family: 'call_application_noop' })
}
for (const size of [0, 32, 128, 512, 2048]) {
  for (const iterations of [1, 10]) {
    cases.push({ name: `call_application_echo_${size}_x${iterations}`, args: ['call-echo', calleeApp, String(size), String(iterations)], iterations, family: 'call_application_echo', size })
  }
}
for (const kind of ['amount', 'account-amount', 'pool-like-small', 'bytes512', 'bytes2048']) {
  for (const iterations of [1, 10]) {
    cases.push({ name: `call_application_decode_${kind}_x${iterations}`, args: ['call-decode', calleeApp, kind, String(iterations)], iterations, family: 'call_application_decode', kind })
  }
}

async function gql(query, variables) {
  const response = await fetch(rpcUrl, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ query, variables }),
  })
  const text = await response.text()
  let parsed
  try { parsed = JSON.parse(text) } catch (e) { throw new Error(`Non-JSON response: ${text}`) }
  if (parsed.errors?.length) throw new Error(JSON.stringify(parsed.errors))
  return parsed.data
}

function opBytes(args) {
  const hex = execFileSync(opgen, args, { encoding: 'utf8' }).trim()
  return Array.from(Buffer.from(hex, 'hex'))
}

function decimalToUnits(value) {
  const text = String(value)
  const [whole, frac = ''] = text.split('.')
  return BigInt(whole + frac.padEnd(18, '0').slice(0, 18))
}

function unitsToDecimal(units) {
  const sign = units < 0n ? '-' : ''
  const abs = units < 0n ? -units : units
  const whole = abs / 1000000000000000000n
  const frac = String(abs % 1000000000000000000n).padStart(18, '0').replace(/0+$/, '')
  return sign + String(whole) + (frac ? `.${frac}` : '')
}

const materialQuery = `query blockMaterialWithDefaultChain($chainId: ChainId, $maxPendingMessages: Int!) {
  blockMaterialWithDefaultChain(chainId: $chainId, maxPendingMessages: $maxPendingMessages) {
    incomingBundles { action origin bundle { height timestamp certificateHash transactionIndex messages { authenticatedSigner grant refundGrantTo kind index message messageMetadata { messageType applicationId userBytesHex systemMessage { systemMessageType credit { target amount source } withdraw { owner amount recipient } } } } } }
    localTime
    round
  }
}`

const estimateQuery = `query estimateGas($chainId: ChainId, $blockMaterial: BlockMaterial!) {
  estimateGas(chainId: $chainId, blockMaterial: $blockMaterial)
}`

const { blockMaterialWithDefaultChain: candidate } = await gql(materialQuery, { chainId, maxPendingMessages: 2 })

const rows = []
for (const testCase of cases) {
  const bytes = opBytes(testCase.args)
  const operation = { User: { applicationId: callerApp, bytes } }
  const data = await gql(estimateQuery, {
    chainId,
    blockMaterial: { operations: [operation], blobBytes: [], candidate },
  })
  rows.push({
    name: testCase.name,
    family: testCase.family,
    kind: testCase.kind || '',
    size: testCase.size ?? '',
    iterations: testCase.iterations,
    gas: String(data.estimateGas),
    gasUnits: String(decimalToUnits(data.estimateGas)),
    operationBytes: bytes.length,
  })
}

const baseline = rows.find(row => row.name === 'noop')
const baselineUnits = BigInt(baseline.gasUnits)
const enriched = rows.map(row => {
  const units = BigInt(row.gasUnits)
  const deltaUnits = units - baselineUnits
  const perIterUnits = deltaUnits / BigInt(row.iterations || 1)
  return {
    ...row,
    delta: unitsToDecimal(deltaUnits),
    deltaUnits: String(deltaUnits),
    perIter: unitsToDecimal(perIterUnits),
    perIterUnits: String(perIterUnits),
  }
})

console.table(enriched.map(({ name, gas, delta, perIter, iterations, operationBytes }) => ({
  name,
  gas,
  delta,
  perIter,
  iterations,
  operationBytes,
})))
console.log(JSON.stringify({ rpcUrl, chainId, callerApp, calleeApp, baseline: baseline.gas, rows: enriched }, null, 2))
