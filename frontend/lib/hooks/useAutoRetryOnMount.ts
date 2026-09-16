import { useEffect, useRef } from 'react'

/**
 * Fires `action` exactly once on mount, regardless of reference changes.
 * The action ref is kept up-to-date so the mounted version always runs the
 * latest closure — same pattern as useDebouncedSearch.
 *
 * Intended for banners/widgets that must trigger a side-effect automatically
 * (activate subscription, retry payment) without risk of double-firing on
 * re-renders or prop changes.
 */
export function useAutoRetryOnMount(action: () => void | Promise<void>) {
  const attempted = useRef(false)
  const actionRef = useRef(action)

  useEffect(() => {
    actionRef.current = action
  })

  useEffect(() => {
    if (attempted.current) return
    attempted.current = true
    void actionRef.current()
  }, [])
}
