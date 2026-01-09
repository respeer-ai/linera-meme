export const timestamp2HumanReadable = (timestamp: number) => {
  const now = Date.now() / 1000
  const timestampSec = timestamp / 1000000
  if (now - timestampSec < 60) {
    return `Before ${Math.floor(now - timestampSec)} seconds`
  }
  if (now - timestampSec < 3600) {
    return `Before ${Math.floor((now - timestampSec) / 60)} minutes`
  }
  if (now - timestampSec < 3600 * 24) {
    return `Before ${Math.floor((now - timestampSec) / 3600)} hours`
  }
  return `Before ${Math.floor((now - timestampSec) / 3600 / 24)} days`
}
