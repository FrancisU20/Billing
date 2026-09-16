import { usePathname } from 'expo-router'
import type { AuthUser } from '@/features/auth/types'
import { getAppNavigationItems, type AppNavigationItem } from './items'

export function useNavigationItems(user: AuthUser | null) {
  const pathname = usePathname()
  const items = getAppNavigationItems(user)

  function isActive(item: AppNavigationItem): boolean {
    return pathname.includes(item.activeWhen)
  }

  return { items, isActive }
}
