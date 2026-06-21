import React, { useEffect, useRef } from 'react'
import {
  Animated,
  Easing,
  Platform,
  StyleSheet,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import { LogoBackdrop, LogoMark } from './Logo'

interface LoadingScreenProps {
  label?: string
  size?: number
}

interface LoadingLogoProps {
  size?: number
  showBackdrop?: boolean
  markColor?: string
  style?: StyleProp<ViewStyle>
}

const AnimatedView = Animated.View
const useNativeDriver = Platform.OS !== 'web'
const PULSE_DURATION_MS = 1200

export function LoadingLogo({
  size = 72,
  showBackdrop = true,
  markColor,
  style,
}: LoadingLogoProps) {
  const { isDark } = useTheme()
  const pulse = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, {
          toValue: 1,
          duration: PULSE_DURATION_MS / 2,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver,
        }),
        Animated.timing(pulse, {
          toValue: 0,
          duration: PULSE_DURATION_MS / 2,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver,
        }),
      ]),
    )
    loop.start()
    return () => {
      loop.stop()
    }
  }, [pulse])

  const scale = pulse.interpolate({ inputRange: [0, 1], outputRange: [1, 1.08] })
  const opacity = pulse.interpolate({ inputRange: [0, 1], outputRange: [0.85, 1] })

  return (
    <View style={[styles.logo, { width: size, height: size }, style]}>
      {showBackdrop ? (
        <LogoBackdrop isDark={isDark} size={size} style={StyleSheet.absoluteFill} />
      ) : null}

      <AnimatedView style={[StyleSheet.absoluteFill, { transform: [{ scale }], opacity }]}>
        <LogoMark isDark={isDark} size={size} color={markColor} />
      </AnimatedView>
    </View>
  )
}

/** Pantalla de carga con la marca Wali pulsando suavemente. */
export function LoadingScreen({ label, size = 120 }: LoadingScreenProps) {
  const { semantic } = useTheme()

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.primary }]}>
      <LoadingLogo size={size} />

      {label ? (
        <Text style={[styles.label, { color: semantic.text.secondary }]}>{label}</Text>
      ) : null}
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: spacing[5] },
  logo: { position: 'relative' },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
})
