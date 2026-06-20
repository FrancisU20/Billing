import { useEffect, useRef } from 'react'

interface UseDebouncedSearchOptions {
  minLength?: number
  debounceMs?: number
}

/**
 * Emite `onSearchChange` con debounce, solo cuando el texto consultable cambia.
 * No depende de la identidad de `onSearchChange` (se guarda en un ref) para que
 * un consumidor que la recrea en cada render no reinicie el timer ni dispare
 * busquedas duplicadas.
 */
export function useDebouncedSearch(
  value: string,
  onSearchChange: (query: string) => void,
  { minLength = 3, debounceMs = 400 }: UseDebouncedSearchOptions = {},
) {
  const query = value.trim()
  const onSearchChangeRef = useRef(onSearchChange)
  const lastEmittedRef = useRef(query)

  useEffect(() => {
    onSearchChangeRef.current = onSearchChange
  }, [onSearchChange])

  useEffect(() => {
    if (query.length === 0) {
      if (lastEmittedRef.current !== '') {
        lastEmittedRef.current = ''
        onSearchChangeRef.current('')
      }
      return undefined
    }

    if (query.length < minLength) return undefined

    const timeout = setTimeout(() => {
      if (lastEmittedRef.current === query) return
      lastEmittedRef.current = query
      onSearchChangeRef.current(query)
    }, debounceMs)

    return () => clearTimeout(timeout)
  }, [query, minLength, debounceMs])

  return {
    shouldWaitForMoreCharacters: query.length > 0 && query.length < minLength,
  }
}
