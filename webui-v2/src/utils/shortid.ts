export const shortId = (
  id: string,
  headNumber: number,
  tailNumber?: number
) => {
  if (!id?.length) return ''
  return id.slice(0, headNumber) + '...' + id.slice(-(tailNumber || 4))
}
