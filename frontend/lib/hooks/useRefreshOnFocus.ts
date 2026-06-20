import { useEffect, useRef } from 'react'
import { useNavigation } from 'expo-router'

interface UseRefreshOnFocusOptions {
  enabled?: boolean
  skipInitial?: boolean
}

export function useRefreshOnFocus(
  refresh: () => void | Promise<void>,
  { enabled = true, skipInitial = true }: UseRefreshOnFocusOptions = {},
) {
  const navigation = useNavigation()
  const refreshRef = useRef(refresh)
  const didFocusRef = useRef(false)

  useEffect(() => {
    refreshRef.current = refresh
  }, [refresh])

  useEffect(() => {
    if (!enabled) return undefined

    return navigation.addListener('focus', () => {
      if (skipInitial && !didFocusRef.current) {
        didFocusRef.current = true
        return
      }
      didFocusRef.current = true
      void refreshRef.current()
    })
  }, [enabled, navigation, skipInitial])
}
