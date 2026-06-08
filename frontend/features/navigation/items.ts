import type { Ionicons } from '@expo/vector-icons'
import { Routes } from '@/constants/routes'
import type { AuthUser } from '@/features/auth/types'

export interface AppNavigationItem {
  label: string
  icon: keyof typeof Ionicons.glyphMap
  href: string
  activeWhen: string
}

const superadminNavigation: AppNavigationItem[] = [
  {
    label: 'Empresas',
    icon: 'business-outline',
    href: Routes.superadmin.tenants,
    activeWhen: '/tenants',
  },
  {
    label: 'Planes',
    icon: 'pricetags-outline',
    href: Routes.superadmin.plans,
    activeWhen: '/plans',
  },
]

const tenantNavigation: AppNavigationItem[] = [
  {
    label: 'Dashboard',
    icon: 'grid-outline',
    href: Routes.tenant.dashboard,
    activeWhen: '/dashboard',
  },
]

export function getAppNavigationItems(user: AuthUser | null): AppNavigationItem[] {
  if (!user) return []
  return user.isSuperadmin ? superadminNavigation : tenantNavigation
}
