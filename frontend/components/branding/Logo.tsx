import React, { useId } from 'react'
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native'
import Svg, { Circle, Defs, Ellipse, Path, RadialGradient, Rect, Stop } from 'react-native-svg'
import { useTheme } from '@/lib/theme-context'
import { brand } from '@/constants/tokens'

interface LogoProps {
  size?: number
  style?: StyleProp<ViewStyle>
}

export const LOGO_C_PATH = 'M 300 116 A 130 130 0 1 0 300 284 L 259 250 A 77 77 0 1 1 259 150 Z'

export const LOGO_PARTICLES = [
  { cx: 319, cy: 100, r: 10, opacity: { light: 1, dark: 1 } },
  { cx: 346, cy: 147, r: 6.5, opacity: { light: 0.75, dark: 0.8 } },
  { cx: 355, cy: 200, r: 4, opacity: { light: 0.45, dark: 0.5 } },
  { cx: 346, cy: 253, r: 6.5, opacity: { light: 0.75, dark: 0.8 } },
  { cx: 319, cy: 300, r: 10, opacity: { light: 1, dark: 1 } },
] as const

interface LogoPieceProps {
  isDark: boolean
  size: number
  style?: StyleProp<ViewStyle>
  color?: string
}

function useSvgId(prefix: string) {
  const id = useId().replace(/[^a-zA-Z0-9_-]/g, '')
  return `${prefix}-${id}`
}

export function LogoBackdrop({ isDark, size, style }: LogoPieceProps) {
  const gradientId = useSvgId('logo-gradient')
  const glowId = useSvgId('logo-glow')
  const gradient = isDark ? brand.gradient.dark : brand.gradient.light

  return (
    <Svg width={size} height={size} viewBox="0 0 400 400" style={style}>
      <Defs>
        <RadialGradient id={gradientId} cx="38%" cy="30%" r="70%">
          <Stop offset="0%" stopColor={gradient.from} />
          <Stop offset="100%" stopColor={gradient.to} />
        </RadialGradient>
        {isDark ? (
          <RadialGradient id={glowId} cx="50%" cy="50%" r="50%">
            <Stop offset="0%" stopColor={brand.glow} stopOpacity={0.15} />
            <Stop offset="100%" stopColor={brand.glow} stopOpacity={0} />
          </RadialGradient>
        ) : null}
      </Defs>

      <Rect x={0} y={0} width={400} height={400} rx={72} fill={`url(#${gradientId})`} />
      {isDark ? <Ellipse cx={190} cy={200} rx={160} ry={160} fill={`url(#${glowId})`} /> : null}
    </Svg>
  )
}

export function LogoMark({ isDark, size, style, color }: LogoPieceProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 400 400" style={style}>
      <Path d={LOGO_C_PATH} fill={color ?? (isDark ? brand.mark.dark : brand.mark.light)} />
    </Svg>
  )
}

export function LogoParticles({ isDark, size, style, color }: LogoPieceProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 400 400" style={style}>
      {LOGO_PARTICLES.map((particle) => (
        <Circle
          key={`${particle.cx}-${particle.cy}`}
          cx={particle.cx}
          cy={particle.cy}
          r={particle.r}
          fill={color ?? (isDark ? brand.particle.dark : brand.particle.light)}
          opacity={isDark ? particle.opacity.dark : particle.opacity.light}
        />
      ))}
    </Svg>
  )
}

/** Marca Codelabs Ecuador: "C" con particulas orbitales, version light/dark segun tema. */
export function Logo({ size = 40, style }: LogoProps) {
  const { isDark } = useTheme()

  return (
    <View style={[styles.container, { width: size, height: size }, style]}>
      <LogoBackdrop isDark={isDark} size={size} />
      <LogoMark isDark={isDark} size={size} style={StyleSheet.absoluteFill} />
      <LogoParticles isDark={isDark} size={size} style={StyleSheet.absoluteFill} />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { position: 'relative' },
})
