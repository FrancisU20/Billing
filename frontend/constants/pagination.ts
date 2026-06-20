export const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
export type PageSize = (typeof PAGE_SIZE_OPTIONS)[number]

export const DEFAULT_PAGE_SIZE: PageSize = 10

export function normalizePageSize(value: number): PageSize {
  return PAGE_SIZE_OPTIONS.includes(value as PageSize) ? (value as PageSize) : DEFAULT_PAGE_SIZE
}
