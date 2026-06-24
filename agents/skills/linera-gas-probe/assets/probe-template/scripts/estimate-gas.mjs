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

const genericPayloadKinds = [
  { kind: 'amount', size: 8 },
  { kind: 'account-amount', size: 48 },
  { kind: 'pool-like-small', size: 212 },
  { kind: 'bytes512', size: 512 },
  { kind: 'bytes2048', size: 2048 },
]

const cases = [{ name: 'noop', args: ['noop'], family: 'baseline' }]

for (const kind of payloadKinds) {
  cases.push({ name: `bcs_encode_${kind}`, args: ['bcs-encode', kind], family: 'bcs_encode', kind })
  cases.push({ name: `bcs_decode_${kind}`, args: ['bcs-decode', kind], family: 'bcs_decode', kind })
}

cases.push({ name: 'call_application_noop', args: ['call-noop', calleeApp], family: 'call_application_noop' })
for (const size of [0, 32, 128, 512, 2048]) {
  cases.push({ name: `call_application_echo_${size}`, args: ['call-echo', calleeApp, String(size)], family: 'call_application_echo', size })
}

for (const size of [32, 512, 2048]) {
  cases.push({ name: `raw_state_read_bytes${size}`, args: ['raw-state-read', String(size)], family: 'raw_state_read', size })
  cases.push({ name: `raw_state_write_bytes${size}`, args: ['raw-state-write', String(size)], family: 'raw_state_write', size })
}

for (const { kind, size } of genericPayloadKinds) {
  cases.push({ name: `typed_state_read_${kind}`, args: ['typed-state-read', kind], family: 'typed_state_read', kind, size })
  cases.push({ name: `typed_state_write_${kind}`, args: ['typed-state-write', kind], family: 'typed_state_write', kind, size })
  cases.push({ name: `generic_state_bcs_encode_write_${kind}`, args: ['generic-state-bcs-encode-write', kind], family: 'generic_state_bcs_encode_write', kind, size })
  cases.push({ name: `generic_state_read_bcs_decode_${kind}`, args: ['generic-state-read-bcs-decode', kind], family: 'generic_state_read_bcs_decode', kind, size })
  cases.push({ name: `call_application_generic_state_bcs_encode_write_${kind}`, args: ['call-generic-state-bcs-encode-write', calleeApp, kind], family: 'call_application_generic_state_bcs_encode_write', kind, size })
  cases.push({ name: `call_application_generic_state_read_bcs_decode_${kind}`, args: ['call-generic-state-read-bcs-decode', calleeApp, kind], family: 'call_application_generic_state_read_bcs_decode', kind, size })
}

for (const kind of ['amount', 'account-amount', 'pool-like-small', 'bytes512', 'bytes2048']) {
  cases.push({ name: `call_application_decode_${kind}`, args: ['call-decode', calleeApp, kind], family: 'call_application_decode', kind })
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
  const frac = String(abs % 1000000000000000000n).padStart(18, '0')
  return `${sign}${whole}.${frac}`
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
  return {
    ...row,
    delta: unitsToDecimal(deltaUnits),
    deltaUnits: String(deltaUnits),
  }
})

const byName = new Map(enriched.map(row => [row.name, row]))
const rawStateComparisons = []
for (const size of [32, 512, 2048]) {
  const rawRead = byName.get(`raw_state_read_bytes${size}`)
  const rawWrite = byName.get(`raw_state_write_bytes${size}`)
  rawStateComparisons.push({
    size,
    rawReadDelta: rawRead?.delta || '',
    rawWriteDelta: rawWrite?.delta || '',
    rawReadDeltaUnits: rawRead?.deltaUnits || '',
    rawWriteDeltaUnits: rawWrite?.deltaUnits || '',
  })
}

const genericComparisons = []
for (const { kind, size } of genericPayloadKinds) {
  const bcsEncode = byName.get(`bcs_encode_${kind}`)
  const bcsDecode = byName.get(`bcs_decode_${kind}`)
  const rawSize = [32, 512, 2048].includes(size) ? size : ''
  const rawRead = rawSize ? byName.get(`raw_state_read_bytes${rawSize}`) : undefined
  const rawWrite = rawSize ? byName.get(`raw_state_write_bytes${rawSize}`) : undefined
  const typedRead = byName.get(`typed_state_read_${kind}`)
  const typedWrite = byName.get(`typed_state_write_${kind}`)
  const genericWrite = byName.get(`generic_state_bcs_encode_write_${kind}`)
  const genericRead = byName.get(`generic_state_read_bcs_decode_${kind}`)
  const callGenericWrite = byName.get(`call_application_generic_state_bcs_encode_write_${kind}`)
  const callGenericRead = byName.get(`call_application_generic_state_read_bcs_decode_${kind}`)
  genericComparisons.push({
    kind,
    size,
    rawReadDelta: rawRead?.delta || '',
    rawWriteDelta: rawWrite?.delta || '',
    typedReadDelta: typedRead?.delta || '',
    typedWriteDelta: typedWrite?.delta || '',
    bcsEncodeDelta: bcsEncode?.delta || '',
    bcsDecodeDelta: bcsDecode?.delta || '',
    genericWriteDelta: genericWrite?.delta || '',
    genericReadDelta: genericRead?.delta || '',
    callGenericWriteDelta: callGenericWrite?.delta || '',
    callGenericReadDelta: callGenericRead?.delta || '',
    typedReadDeltaUnits: typedRead?.deltaUnits || '',
    typedWriteDeltaUnits: typedWrite?.deltaUnits || '',
    genericWriteDeltaUnits: genericWrite?.deltaUnits || '',
    genericReadDeltaUnits: genericRead?.deltaUnits || '',
    callGenericWriteDeltaUnits: callGenericWrite?.deltaUnits || '',
    callGenericReadDeltaUnits: callGenericRead?.deltaUnits || '',
  })
}

console.table(enriched.map(({ name, gas, delta, operationBytes }) => ({
  name,
  gas,
  delta,
  operationBytes,
})))
console.table(rawStateComparisons.map(({ size, rawReadDelta, rawWriteDelta }) => ({
  size,
  rawReadDelta,
  rawWriteDelta,
})))
console.table(genericComparisons.map(({
  kind,
  size,
  rawReadDelta,
  rawWriteDelta,
  typedReadDelta,
  typedWriteDelta,
  bcsEncodeDelta,
  bcsDecodeDelta,
  genericWriteDelta,
  genericReadDelta,
  callGenericWriteDelta,
  callGenericReadDelta,
}) => ({
  kind,
  size,
  rawReadDelta,
  rawWriteDelta,
  typedReadDelta,
  typedWriteDelta,
  bcsEncodeDelta,
  bcsDecodeDelta,
  genericWriteDelta,
  genericReadDelta,
  callGenericWriteDelta,
  callGenericReadDelta,
})))
console.log(JSON.stringify({ rpcUrl, chainId, callerApp, calleeApp, baseline: baseline.gas, rows: enriched, rawStateComparisons, genericComparisons }, null, 2))
