export const Routes = {
  root: '/' as const,
  auth: {
    login: '/(auth)/login' as const,
    challenge: '/(auth)/challenge' as const,
  },
  public: {
    pricing: '/(public)/pricing' as const,
  },
  app: {
    profile: '/(app)/profile' as const,
  },
  superadmin: {
    tenants: '/(app)/(superadmin)/tenants' as const,
    tenantNew: '/(app)/(superadmin)/tenants/new' as const,
    tenantDetail: (id: string) => `/(app)/(superadmin)/tenants/${id}` as const,
    plans: '/(app)/(superadmin)/plans' as const,
    planNew: '/(app)/(superadmin)/plans/new' as const,
  },
  tenant: {
    dashboard: '/(app)/(tenant)/dashboard' as const,
  },
} as const
