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

const genericPayloadKinds = [
  { kind: 'amount', size: 8 },
  { kind: 'account-amount', size: 48 },
  { kind: 'pool-like-small', size: 212 },
  { kind: 'bytes512', size: 512 },
  { kind: 'bytes2048', size: 2048 },
]

for (const size of [32, 512, 2048]) {
  for (const iterations of [1, 10]) {
    cases.push({ name: `raw_state_read_bytes${size}_x${iterations}`, args: ['raw-state-read', String(size), String(iterations)], iterations, family: 'raw_state_read', size })
    cases.push({ name: `raw_state_write_bytes${size}_x${iterations}`, args: ['raw-state-write', String(size), String(iterations)], iterations, family: 'raw_state_write', size })
  }
}
for (const { kind, size } of genericPayloadKinds) {
  for (const iterations of [1, 10]) {
    cases.push({ name: `typed_state_read_${kind}_x${iterations}`, args: ['typed-state-read', kind, String(iterations)], iterations, family: 'typed_state_read', kind, size })
    cases.push({ name: `typed_state_write_${kind}_x${iterations}`, args: ['typed-state-write', kind, String(iterations)], iterations, family: 'typed_state_write', kind, size })
    cases.push({ name: `generic_state_bcs_encode_write_${kind}_x${iterations}`, args: ['generic-state-bcs-encode-write', kind, String(iterations)], iterations, family: 'generic_state_bcs_encode_write', kind, size })
    cases.push({ name: `generic_state_read_bcs_decode_${kind}_x${iterations}`, args: ['generic-state-read-bcs-decode', kind, String(iterations)], iterations, family: 'generic_state_read_bcs_decode', kind, size })
    cases.push({ name: `call_application_generic_state_bcs_encode_write_${kind}_x${iterations}`, args: ['call-generic-state-bcs-encode-write', calleeApp, kind, String(iterations)], iterations, family: 'call_application_generic_state_bcs_encode_write', kind, size })
    cases.push({ name: `call_application_generic_state_read_bcs_decode_${kind}_x${iterations}`, args: ['call-generic-state-read-bcs-decode', calleeApp, kind, String(iterations)], iterations, family: 'call_application_generic_state_read_bcs_decode', kind, size })
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

const byName = new Map(enriched.map(row => [row.name, row]))
const rawStateComparisons = []
for (const size of [32, 512, 2048]) {
  for (const iterations of [1, 10]) {
    const rawRead = byName.get(`raw_state_read_bytes${size}_x${iterations}`)
    const rawWrite = byName.get(`raw_state_write_bytes${size}_x${iterations}`)
    rawStateComparisons.push({
      size,
      iterations,
      rawReadPerIter: rawRead?.perIter || '',
      rawWritePerIter: rawWrite?.perIter || '',
      rawReadDeltaUnits: rawRead?.deltaUnits || '',
      rawWriteDeltaUnits: rawWrite?.deltaUnits || '',
    })
  }
}

const genericComparisons = []
for (const { kind, size } of genericPayloadKinds) {
  const bcsEncode = byName.get(`bcs_encode_${kind}_x100`)
  const bcsDecode = byName.get(`bcs_decode_${kind}_x100`)
  const rawSize = [32, 512, 2048].includes(size) ? size : ''
  for (const iterations of [1, 10]) {
    const rawRead = rawSize ? byName.get(`raw_state_read_bytes${rawSize}_x${iterations}`) : undefined
    const rawWrite = rawSize ? byName.get(`raw_state_write_bytes${rawSize}_x${iterations}`) : undefined
    const typedRead = byName.get(`typed_state_read_${kind}_x${iterations}`)
    const typedWrite = byName.get(`typed_state_write_${kind}_x${iterations}`)
    const genericWrite = byName.get(`generic_state_bcs_encode_write_${kind}_x${iterations}`)
    const genericRead = byName.get(`generic_state_read_bcs_decode_${kind}_x${iterations}`)
    const callGenericWrite = byName.get(`call_application_generic_state_bcs_encode_write_${kind}_x${iterations}`)
    const callGenericRead = byName.get(`call_application_generic_state_read_bcs_decode_${kind}_x${iterations}`)
    genericComparisons.push({
      kind,
      size,
      iterations,
      rawReadPerIter: rawRead?.perIter || '',
      rawWritePerIter: rawWrite?.perIter || '',
      typedReadPerIter: typedRead?.perIter || '',
      typedWritePerIter: typedWrite?.perIter || '',
      bcsEncodePerIter: bcsEncode?.perIter || '',
      bcsDecodePerIter: bcsDecode?.perIter || '',
      genericWritePerIter: genericWrite?.perIter || '',
      genericReadPerIter: genericRead?.perIter || '',
      callGenericWritePerIter: callGenericWrite?.perIter || '',
      callGenericReadPerIter: callGenericRead?.perIter || '',
      typedReadDeltaUnits: typedRead?.deltaUnits || '',
      typedWriteDeltaUnits: typedWrite?.deltaUnits || '',
      genericWriteDeltaUnits: genericWrite?.deltaUnits || '',
      genericReadDeltaUnits: genericRead?.deltaUnits || '',
      callGenericWriteDeltaUnits: callGenericWrite?.deltaUnits || '',
      callGenericReadDeltaUnits: callGenericRead?.deltaUnits || '',
    })
  }
}

console.table(enriched.map(({ name, gas, delta, perIter, iterations, operationBytes }) => ({
  name,
  gas,
  delta,
  perIter,
  iterations,
  operationBytes,
})))
console.table(rawStateComparisons.map(({
  size,
  iterations,
  rawReadPerIter,
  rawWritePerIter,
}) => ({
  size,
  iterations,
  rawReadPerIter,
  rawWritePerIter,
})))
console.table(genericComparisons.map(({
  kind,
  size,
  iterations,
  rawReadPerIter,
  rawWritePerIter,
  typedReadPerIter,
  typedWritePerIter,
  bcsEncodePerIter,
  bcsDecodePerIter,
  genericWritePerIter,
  genericReadPerIter,
  callGenericWritePerIter,
  callGenericReadPerIter,
}) => ({
  kind,
  size,
  iterations,
  rawReadPerIter,
  rawWritePerIter,
  typedReadPerIter,
  typedWritePerIter,
  bcsEncodePerIter,
  bcsDecodePerIter,
  genericWritePerIter,
  genericReadPerIter,
  callGenericWritePerIter,
  callGenericReadPerIter,
})))
console.log(JSON.stringify({ rpcUrl, chainId, callerApp, calleeApp, baseline: baseline.gas, rows: enriched, rawStateComparisons, genericComparisons }, null, 2))
