export const timestamp2HumanReadable = (timestamp: number) => {
  const now = Date.now() / 1000
  const timestampSec = timestamp / 1000000
  if (now - timestampSec < 60) {
    return {
      msg: 'MSG_BEFORE_SECONDS',
      value: Math.floor(now - timestampSec),
    }
  }
  if (now - timestampSec < 3600) {
    return {
      msg: 'MSG_BEFORE_MINUTES',
      value: Math.floor((now - timestampSec) / 60),
    }
  }
  if (now - timestampSec < 3600 * 24) {
    return {
      msg: 'MSG_BEFORE_HOURS',
      value: Math.floor((now - timestampSec) / 3600),
    }
  }
  return {
    msg: 'MSG_BEFORE_DAYS',
    value: Math.floor((now - timestampSec) / 3600 / 24),
  }
}
