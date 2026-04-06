export type LoadDirection = 'new' | 'old'

export const enqueueLoadDirection = (
  queue: LoadDirection[],
  direction: LoadDirection,
): LoadDirection[] => (queue.includes(direction) ? queue : [...queue, direction])

export const dequeueLoadDirection = (
  queue: LoadDirection[],
): { next: LoadDirection | null; remaining: LoadDirection[] } => {
  if (queue.length === 0) {
    return {
      next: null,
      remaining: [],
    }
  }

  return {
    next: queue[0] ?? null,
    remaining: queue.slice(1),
  }
}
