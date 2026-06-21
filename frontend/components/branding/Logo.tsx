import React from 'react'
import { StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native'
import Svg, { G, Path, Rect } from 'react-native-svg'
import { useTheme } from '@/lib/theme-context'
import { brand } from '@/constants/tokens'

interface LogoProps {
  size?: number
  style?: StyleProp<ViewStyle>
}

export const LOGO_W_TRANSFORM = 'translate(117.8,355.9) scale(0.3647,-0.3647)'

export const LOGO_W_PATHS = [
  'M79.0,469.0 L229.0,79.0 L379.0,469.0',
  'M379.0,469.0 L529.0,79.0 L679.0,469.0',
] as const

interface LogoPieceProps {
  isDark: boolean
  size: number
  style?: StyleProp<ViewStyle>
  color?: string
}

export function LogoBackdrop({ isDark, size, style }: LogoPieceProps) {
  const fill = isDark ? brand.surface.dark : brand.surface.light

  return (
    <Svg width={size} height={size} viewBox="0 0 512 512" style={style}>
      <Rect width={512} height={512} rx={114.5} ry={114.5} fill={fill} />
    </Svg>
  )
}

export function LogoMark({ isDark, size, style, color }: LogoPieceProps) {
  const accentColor = color ?? brand.accent
  const inkColor = color ?? (isDark ? brand.ink.dark : brand.ink.light)

  return (
    <Svg width={size} height={size} viewBox="0 0 512 512" style={style}>
      <G
        transform={LOGO_W_TRANSFORM}
        fill="none"
        strokeWidth={158}
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <Path d={LOGO_W_PATHS[0]} stroke={accentColor} />
        <Path d={LOGO_W_PATHS[1]} stroke={inkColor} />
      </G>
    </Svg>
  )
}

/** Marca Wali: "W" de doble trazo morado/tinta sobre fondo plano, version light/dark segun tema. */
export function Logo({ size = 40, style }: LogoProps) {
  const { isDark } = useTheme()

  return (
    <View style={[styles.container, { width: size, height: size }, style]}>
      <LogoBackdrop isDark={isDark} size={size} />
      <LogoMark isDark={isDark} size={size} style={StyleSheet.absoluteFill} />
    </View>
  )
}

const WORDMARK_VIEW_BOX = '0 0 2226 880'
const WORDMARK_ASPECT_RATIO = 2226 / 880

const WORDMARK_LETTER_PATHS = [
  {
    transform: 'translate(776,0)',
    d:
      'M286 563Q348 563 394.5 538.0Q441 513 469 475V554H610V0H469V81Q442 42 394.5 16.5Q347 -9 285 -9' +
      'Q215 -9 157.5 27.0Q100 63 66.5 128.5Q33 194 33 279Q33 363 66.5 428.0Q100 493 157.5 528.0Q215 563 286 563ZM322 440' +
      'Q283 440 250.0 421.0Q217 402 196.5 365.5Q176 329 176 279Q176 229 196.5 191.5Q217 154 250.5 134.0Q284 114 322 114' +
      'Q361 114 395.0 133.5Q429 153 449.0 189.5Q469 226 469 277Q469 328 449.0 364.5Q429 401 395.0 420.5Q361 440 322 440Z',
  },
  { transform: 'translate(1472,0)', d: 'M209 740V0H69V740Z' },
  {
    transform: 'translate(1768,0)',
    d:
      'M54 702Q54 737 78.5 760.5Q103 784 140 784Q177 784 201.5 760.5Q226 737 226 702Q226 667 201.5 643.5' +
      'Q177 620 140 620Q103 620 78.5 643.5Q54 667 54 702ZM209 554V0H69V554Z',
  },
] as const

interface WordmarkProps {
  height?: number
  style?: StyleProp<ViewStyle>
  /** Color unico para W + lettering (modo monocromo, ignora el morado de marca). */
  color?: string
  /** Color del lettering "ali" y el segundo trazo de la W cuando la superficie es fija (no sigue el tema). */
  ink?: string
}

/** Logotipo Wali: "W" de doble trazo + lettering "ali", como una sola pieza (sin caja de icono). */
export function Wordmark({ height = 32, style, color, ink }: WordmarkProps) {
  const { isDark } = useTheme()
  const accentColor = color ?? brand.accent
  const inkColor = color ?? ink ?? (isDark ? brand.ink.dark : brand.ink.light)

  return (
    <Svg
      width={height * WORDMARK_ASPECT_RATIO}
      height={height}
      viewBox={WORDMARK_VIEW_BOX}
      style={style}
    >
      <G transform="translate(90,790) scale(1,-1)">
        <G fill="none" strokeWidth={158} strokeLinecap="round" strokeLinejoin="round">
          <Path d={LOGO_W_PATHS[0]} stroke={accentColor} />
          <Path d={LOGO_W_PATHS[1]} stroke={inkColor} />
        </G>
        {WORDMARK_LETTER_PATHS.map((letter) => (
          <Path key={letter.transform} transform={letter.transform} d={letter.d} fill={inkColor} />
        ))}
      </G>
    </Svg>
  )
}

const styles = StyleSheet.create({
  container: { position: 'relative' },
})
