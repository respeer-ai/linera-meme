type TimerHandle = ReturnType<typeof setTimeout> | number

type IndicatorRenderSchedulerOptions = {
  schedule: (run: () => void) => TimerHandle
  cancel: (handle: TimerHandle) => void
  run: (signature: string) => void
}

export const createIndicatorRenderScheduler = ({
  schedule,
  cancel,
  run,
}: IndicatorRenderSchedulerOptions) => {
  let renderedSignature: string | null = null
  let pendingSignature: string | null = null
  let pendingHandle: TimerHandle | null = null

  const clear = () => {
    if (pendingHandle !== null) {
      cancel(pendingHandle)
    }
    pendingHandle = null
    pendingSignature = null
    renderedSignature = null
  }

  const request = (signature: string) => {
    if (renderedSignature === signature && pendingHandle === null) {
      return false
    }

    if (pendingHandle !== null) {
      cancel(pendingHandle)
      pendingHandle = null
    }

    pendingSignature = signature
    pendingHandle = schedule(() => {
      pendingHandle = null
      if (!pendingSignature) return

      const nextSignature = pendingSignature
      pendingSignature = null
      renderedSignature = nextSignature
      run(nextSignature)
    })

    return true
  }

  return {
    clear,
    getRenderedSignature: () => renderedSignature,
    request,
  }
}
