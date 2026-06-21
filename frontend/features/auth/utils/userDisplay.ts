import { RoleLabel } from '@/constants/roles'
import type { AuthUser } from '../types'

export function getUserInitial(user: Pick<AuthUser, 'email'> | null): string {
  return user?.email.charAt(0).toUpperCase() || 'U'
}

export function getUserRoleLabel(user: Pick<AuthUser, 'role'> | null): string {
  return user ? RoleLabel[user.role] : 'Usuario'
}
