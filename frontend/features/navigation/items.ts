import type { Ionicons } from '@expo/vector-icons'
import { Routes } from '@/constants/routes'
import type { AuthUser } from '@/features/auth/types'

export interface AppNavigationItem {
  label: string
  icon: keyof typeof Ionicons.glyphMap
  href: string
  activeWhen: string
}

// Deriva el segmento final de una ruta de Routes para usar con pathname.includes().
// Si la ruta cambia en Routes, activeWhen se actualiza automáticamente.
function segment(route: string): string {
  return '/' + route.split('/').pop()!
}

const superadminNavigation: AppNavigationItem[] = [
  {
    label: 'Empresas',
    icon: 'business-outline',
    href: Routes.superadmin.tenants,
    activeWhen: segment(Routes.superadmin.tenants),
  },
  {
    label: 'Planes',
    icon: 'pricetags-outline',
    href: Routes.superadmin.plans,
    activeWhen: segment(Routes.superadmin.plans),
  },
]

const tenantNavigation: AppNavigationItem[] = [
  {
    label: 'Dashboard',
    icon: 'grid-outline',
    href: Routes.tenant.dashboard,
    activeWhen: segment(Routes.tenant.dashboard),
  },
]

export function getAppNavigationItems(user: AuthUser | null): AppNavigationItem[] {
  if (!user) return []
  return user.isSuperadmin ? superadminNavigation : tenantNavigation
}
