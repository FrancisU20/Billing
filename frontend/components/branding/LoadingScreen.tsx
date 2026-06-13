import React, { useEffect, useRef } from 'react'
import { Animated, Easing, Platform, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { spacing, typography } from '@/constants/tokens'
import { LogoBackdrop, LogoMark, LogoParticles } from './Logo'

interface LoadingScreenProps {
  label?: string
  size?: number
}

interface LoadingLogoProps {
  size?: number
}

const AnimatedView = Animated.View
const useNativeDriver = Platform.OS !== 'web'
const PARTICLE_ROTATION_DURATION_MS = 6000
const PARTICLE_ORBIT_SCALE = 1.08

export function LoadingLogo({ size = 72 }: LoadingLogoProps) {
  const { isDark } = useTheme()
  const rotation = useRef(new Animated.Value(0)).current

  useEffect(() => {
    const spin = Animated.loop(
      Animated.timing(rotation, {
        toValue: 1,
        duration: PARTICLE_ROTATION_DURATION_MS,
        easing: Easing.linear,
        useNativeDriver,
      }),
    )
    spin.start()
    return () => {
      spin.stop()
    }
  }, [rotation])

  const spin = rotation.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] })

  return (
    <View style={[styles.logo, { width: size, height: size }]}>
      <LogoBackdrop isDark={isDark} size={size} style={StyleSheet.absoluteFill} />

      <View style={StyleSheet.absoluteFill}>
        <LogoMark isDark={isDark} size={size} />
      </View>

      <AnimatedView
        style={[
          StyleSheet.absoluteFill,
          { transform: [{ rotate: spin }, { scale: PARTICLE_ORBIT_SCALE }] },
        ]}
      >
        <LogoParticles isDark={isDark} size={size} />
      </AnimatedView>
    </View>
  )
}

/** Pantalla de carga animada con la C fija y particulas orbitando. */
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
