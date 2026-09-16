import { useCallback, useEffect, useRef, useState } from 'react'
import { toApiError, type ApiError } from '@/lib/api/errors'

/**
 * Manages shared state for search-with-quick-create picker modals.
 * Handles: query, results, search anti-race pattern, loading/error/creating,
 * showQuickCreate toggle, and reset on open.
 *
 * The caller supplies the search API fn and a resetExtras callback for domain-specific
 * quick-form fields; everything else is shared.
 */
export function usePickerSearchState<T>(
  visible: boolean,
  onClose: () => void,
  searchFn: (q: string) => Promise<{ items: T[] }>,
  resetExtras: () => void,
) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<T[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [showQuickCreate, setShowQuickCreate] = useState(false)
  const searchRequestIdRef = useRef(0)
  const searchFnRef = useRef(searchFn)
  const resetExtrasRef = useRef(resetExtras)
  const onCloseRef = useRef(onClose)

  useEffect(() => {
    searchFnRef.current = searchFn
  })
  useEffect(() => {
    resetExtrasRef.current = resetExtras
  })
  useEffect(() => {
    onCloseRef.current = onClose
  })

  const resetCore = useCallback(() => {
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setCreating(false)
    setError(null)
    setShowQuickCreate(false)
  }, [])

  useEffect(() => {
    if (!visible) return
    searchRequestIdRef.current += 1
    resetCore()
    resetExtrasRef.current()
  }, [visible, resetCore])

  const search = useCallback(
    async (nextQuery = query) => {
      const q = nextQuery.trim()
      if (q.length < 3) return
      const requestId = searchRequestIdRef.current + 1
      searchRequestIdRef.current = requestId
      setLoading(true)
      setError(null)
      try {
        const page = await searchFnRef.current(q)
        if (requestId !== searchRequestIdRef.current) return
        setResults(page.items)
        setSearched(true)
      } catch (e) {
        if (requestId !== searchRequestIdRef.current) return
        setError(toApiError(e))
      } finally {
        if (requestId === searchRequestIdRef.current) setLoading(false)
      }
    },
    [query],
  )

  const close = useCallback(() => {
    resetCore()
    resetExtrasRef.current()
    onCloseRef.current()
  }, [resetCore])

  return {
    query,
    setQuery,
    results,
    searched,
    loading,
    creating,
    setCreating,
    error,
    setError,
    showQuickCreate,
    setShowQuickCreate,
    search,
    close,
  }
}
