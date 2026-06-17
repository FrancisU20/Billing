const DEFAULT_DELAYS_MS = [1000, 2000, 4000]

export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  delaysMs: number[] = DEFAULT_DELAYS_MS,
): Promise<T> {
  let lastError: unknown
  for (let attempt = 0; attempt <= delaysMs.length; attempt++) {
    try {
      return await fn()
    } catch (err) {
      lastError = err
      if (attempt < delaysMs.length) {
        await new Promise((resolve) => setTimeout(resolve, delaysMs[attempt]))
      }
    }
  }
  throw lastError
}
