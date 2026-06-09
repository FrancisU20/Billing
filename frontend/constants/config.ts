import Constants from 'expo-constants'

const extra = Constants.expoConfig?.extra ?? {}

const DEV_API_URL = 'https://api-billing-dev.codelabsecuador.com'
const STAGING_API_URL = 'https://api-billing-staging.codelabsecuador.com'
const PROD_API_URL = 'https://api-billing.codelabsecuador.com'

function resolveApiUrl(): string {
  // 1. Variable de entorno en tiempo de build (EXPO_PUBLIC_API_URL=...)
  if (process.env.EXPO_PUBLIC_API_URL) return process.env.EXPO_PUBLIC_API_URL

  // 2. Inyectado desde app.json extra (CI/CD)
  if (extra.apiUrl) return extra.apiUrl as string

  // 3. Dev local usa AWS dev por defecto. Para otro endpoint, usar EXPO_PUBLIC_API_URL.
  if (__DEV__) return DEV_API_URL

  if (extra.env === 'dev') return DEV_API_URL
  if (extra.env === 'staging') return STAGING_API_URL
  return PROD_API_URL
}

export const config = {
  apiUrl: resolveApiUrl(),
  env: (extra.env as 'dev' | 'staging' | 'prod') ?? (__DEV__ ? 'dev' : 'prod'),
} as const
