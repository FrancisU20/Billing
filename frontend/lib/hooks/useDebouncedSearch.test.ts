// @vitest-environment jsdom
import { renderHook, waitFor } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import { useDebouncedSearch } from './useDebouncedSearch'

describe('useDebouncedSearch', () => {
  it('does not emit on mount when the value already starts empty', async () => {
    const onSearchChange = vi.fn()
    renderHook(() => useDebouncedSearch('', onSearchChange))

    await new Promise((resolve) => setTimeout(resolve, 50))
    expect(onSearchChange).not.toHaveBeenCalled()
  })

  it('emits once after the debounce when the query reaches minLength', async () => {
    const onSearchChange = vi.fn()
    const { rerender } = renderHook(({ value }) => useDebouncedSearch(value, onSearchChange), {
      initialProps: { value: '' },
    })

    rerender({ value: 'ab' })
    rerender({ value: 'abc' })

    await waitFor(() => expect(onSearchChange).toHaveBeenCalledTimes(1))
    expect(onSearchChange).toHaveBeenCalledWith('abc')
  })

  it('does not re-emit the same query when only the onSearchChange identity changes', async () => {
    const calls: string[] = []
    const { rerender } = renderHook(
      ({ value, onSearchChange }) => useDebouncedSearch(value, onSearchChange),
      {
        initialProps: { value: '', onSearchChange: (q: string) => calls.push(q) },
      },
    )

    rerender({ value: 'abc', onSearchChange: (q: string) => calls.push(q) })
    await waitFor(() => expect(calls).toEqual(['abc']))

    // simulate a consumer that recreates onSearchChange on every render (no useCallback),
    // exactly like ClientsFilters/ClientPickerModal/etc. do today — should not re-trigger
    rerender({ value: 'abc', onSearchChange: (q: string) => calls.push(q) })
    rerender({ value: 'abc', onSearchChange: (q: string) => calls.push(q) })

    await new Promise((resolve) => setTimeout(resolve, 500))
    expect(calls).toEqual(['abc'])
  })

  it('emits empty string once when the user clears the field, even with zero results found before', async () => {
    const onSearchChange = vi.fn()
    const { rerender } = renderHook(({ value }) => useDebouncedSearch(value, onSearchChange), {
      initialProps: { value: '' },
    })

    rerender({ value: 'xyz' })
    await waitFor(() => expect(onSearchChange).toHaveBeenCalledWith('xyz'))

    rerender({ value: '' })
    await waitFor(() => expect(onSearchChange).toHaveBeenCalledWith(''))
    expect(onSearchChange).toHaveBeenCalledTimes(2)
  })

  it('does not call the backend repeatedly while waiting below minLength', async () => {
    const onSearchChange = vi.fn()
    const { rerender } = renderHook(({ value }) => useDebouncedSearch(value, onSearchChange), {
      initialProps: { value: '' },
    })

    rerender({ value: 'a' })
    rerender({ value: 'ab' })

    await new Promise((resolve) => setTimeout(resolve, 500))
    expect(onSearchChange).not.toHaveBeenCalled()
  })
})
