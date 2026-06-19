import type { Ionicons } from '@expo/vector-icons'
import type { Href } from 'expo-router'
import { Routes } from '@/constants/routes'
import type { AuthUser } from '@/features/auth/types'

export interface AppNavigationItem {
  label: string
  icon: keyof typeof Ionicons.glyphMap
  href: Href
  activeWhen: string
}

// Deriva el segmento final de una ruta de Routes para usar con pathname.includes().
// Si la ruta cambia en Routes, activeWhen se actualiza automáticamente.
function segment(route: string): string {
  const last = route.split('/').pop()
  return last ? `/${last}` : '/'
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
  {
    label: 'Clientes',
    icon: 'people-outline',
    href: Routes.tenant.clients as Href,
    activeWhen: segment(Routes.tenant.clients),
  },
  {
    label: 'Productos',
    icon: 'cube-outline',
    href: Routes.tenant.products as Href,
    activeWhen: segment(Routes.tenant.products),
  },
  {
    label: 'Documentos',
    icon: 'document-text-outline',
    href: Routes.tenant.documents as Href,
    activeWhen: segment(Routes.tenant.documents),
  },
  {
    label: 'Establecimientos',
    icon: 'storefront-outline',
    href: Routes.tenant.establishments as Href,
    activeWhen: segment(Routes.tenant.establishments),
  },
  {
    label: 'Descuento global',
    icon: 'pricetag-outline',
    href: Routes.tenant.discountCampaign as Href,
    activeWhen: segment(Routes.tenant.discountCampaign),
  },
  {
    label: 'Facturación',
    icon: 'card-outline',
    href: Routes.tenant.billing as Href,
    activeWhen: segment(Routes.tenant.billing),
  },
]

export function getAppNavigationItems(user: AuthUser | null): AppNavigationItem[] {
  if (!user) return []
  return user.isSuperadmin ? superadminNavigation : tenantNavigation
}
