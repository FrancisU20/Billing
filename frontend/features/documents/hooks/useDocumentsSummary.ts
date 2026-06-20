import { useCallback } from 'react'
import { useFetch } from '@/lib/hooks/useFetch'
import { documentsApi } from '../api'

export function useDocumentsSummary() {
  const fetcher = useCallback(() => documentsApi.summary(), [])
  const { data, ...state } = useFetch(fetcher)
  return { summary: data, ...state }
}
