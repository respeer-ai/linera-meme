export const trimZeros = (value: string) => {
  if (!value.includes('.')) return value
  while (value[value.length - 1] === '0' && value.length > 0) {
    value = value.substring(0, value.length - 1)
  }
  return value
}
