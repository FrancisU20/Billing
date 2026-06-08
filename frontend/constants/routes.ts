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
    tenantEdit: (id: string) => `/(app)/(superadmin)/tenants/${id}/edit` as const,
    plans: '/(app)/(superadmin)/plans' as const,
    planNew: '/(app)/(superadmin)/plans/new' as const,
    planDetail: (slug: string) => `/(app)/(superadmin)/plans/${slug}` as const,
    planEdit: (slug: string) => `/(app)/(superadmin)/plans/${slug}/edit` as const,
  },
  tenant: {
    dashboard: '/(app)/(tenant)/dashboard' as const,
    clients: '/(app)/(tenant)/clients' as const,
    clientNew: '/(app)/(tenant)/clients/new' as const,
    clientDetail: (id: string) => `/(app)/(tenant)/clients/${id}` as const,
    clientEdit: (id: string) => `/(app)/(tenant)/clients/${id}/edit` as const,
  },
} as const
