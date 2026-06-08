export type AuthRole = 'superadmin' | 'owner' | 'admin' | 'viewer'

export const Role = {
  SUPERADMIN: 'superadmin' as const,
  OWNER: 'owner' as const,
  ADMIN: 'admin' as const,
  VIEWER: 'viewer' as const,
}

export const RoleLabel: Record<AuthRole, string> = {
  superadmin: 'Super Admin',
  owner: 'Propietario',
  admin: 'Administrador',
  viewer: 'Visualizador',
}

export function canWrite(role: AuthRole | null): boolean {
  if (!role) return false
  return role === Role.SUPERADMIN || role === Role.OWNER || role === Role.ADMIN
}

export function canManageTenant(role: AuthRole | null): boolean {
  if (!role) return false
  return role === Role.OWNER
}
