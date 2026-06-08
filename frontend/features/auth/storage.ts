import { Platform } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import type { AuthTokens } from './types'

const KEY_ID_TOKEN = 'cbc_id_token'
const KEY_ACCESS_TOKEN = 'cbc_access_token'
const KEY_REFRESH_TOKEN = 'cbc_refresh_token'

const isBrowser = typeof window !== 'undefined'

async function get(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    if (!isBrowser) return null
    return sessionStorage.getItem(key) ?? localStorage.getItem(key)
  }
  return SecureStore.getItemAsync(key)
}

async function set(key: string, value: string, persistent = false): Promise<void> {
  if (Platform.OS === 'web') {
    if (!isBrowser) return
    if (persistent) {
      localStorage.setItem(key, value)
    } else {
      sessionStorage.setItem(key, value)
    }
    return
  }
  await SecureStore.setItemAsync(key, value)
}

async function remove(key: string): Promise<void> {
  if (Platform.OS === 'web') {
    if (!isBrowser) return
    sessionStorage.removeItem(key)
    localStorage.removeItem(key)
    return
  }
  await SecureStore.deleteItemAsync(key)
}

export const tokenStorage = {
  saveAll: async (tokens: AuthTokens, persistent = false): Promise<void> => {
    await Promise.all([
      set(KEY_ID_TOKEN, tokens.idToken, false),
      set(KEY_ACCESS_TOKEN, tokens.accessToken, false),
      set(KEY_REFRESH_TOKEN, tokens.refreshToken, persistent),
    ])
  },

  loadAll: async (): Promise<AuthTokens | null> => {
    const [idToken, accessToken, refreshToken] = await Promise.all([
      get(KEY_ID_TOKEN),
      get(KEY_ACCESS_TOKEN),
      get(KEY_REFRESH_TOKEN),
    ])
    if (!idToken || !accessToken || !refreshToken) return null
    return { idToken, accessToken, refreshToken }
  },

  clearAll: async (): Promise<void> => {
    await Promise.all([remove(KEY_ID_TOKEN), remove(KEY_ACCESS_TOKEN), remove(KEY_REFRESH_TOKEN)])
  },
}
