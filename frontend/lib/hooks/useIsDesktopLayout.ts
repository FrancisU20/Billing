import { Platform, useWindowDimensions } from 'react-native'
import { breakpoints } from '@/constants/tokens'

/**
 * true solo en web con viewport ancho (sidebar fijo). Mobile (iOS/Android) y web angosto
 * siguen con el menu hamburguesa/drawer (`AppNavBar` + `NavigationMenu`).
 */
export function useIsDesktopLayout(): boolean {
  const { width } = useWindowDimensions()
  return Platform.OS === 'web' && width >= breakpoints.desktop
}
