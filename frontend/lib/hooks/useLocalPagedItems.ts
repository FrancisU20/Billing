import { useCallback, useEffect, useMemo, useState } from 'react'
import { DEFAULT_PAGE_SIZE, type PageSize } from '@/constants/pagination'

export function useLocalPagedItems<T>(items: T[], initialPageSize: PageSize = DEFAULT_PAGE_SIZE) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSizeState] = useState<PageSize>(initialPageSize)
  const totalPages = Math.max(1, Math.ceil(items.length / pageSize))

  useEffect(() => {
    setPage(1)
  }, [items, pageSize])

  const pageItems = useMemo(() => {
    const start = (page - 1) * pageSize
    return items.slice(start, start + pageSize)
  }, [items, page, pageSize])

  const nextPage = useCallback(() => {
    setPage((current) => Math.min(current + 1, totalPages))
  }, [totalPages])

  const previousPage = useCallback(() => {
    setPage((current) => Math.max(current - 1, 1))
  }, [])

  const setPageSize = useCallback((nextPageSize: PageSize) => {
    setPageSizeState(nextPageSize)
  }, [])

  return {
    pageItems,
    page,
    pageSize,
    totalItems: items.length,
    totalPages,
    canGoNext: page < totalPages,
    canGoPrevious: page > 1,
    nextPage,
    previousPage,
    setPageSize,
  }
}
