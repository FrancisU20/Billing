// boxShadow es una propiedad CSS web válida en Expo Web aunque no está
// incluida en el tipo ViewStyle de React Native. Al tipar shadow como
// Record<..., ShadowStyle>, todos los componentes pueden usar shadow.lg
// directamente en arrays de style sin necesitar `as any`.
import type { ViewStyle } from 'react-native'
export type ShadowStyle = ViewStyle & { boxShadow: string }

export const colors = {
  primary: {
    50: '#F1F1FF',
    100: '#E3E2FF',
    200: '#C7C5FF',
    300: '#A29CFF',
    400: '#9994FF',
    500: '#766FFF',
    600: '#4F46FF',
    700: '#3A31EB',
    800: '#2219D4',
    900: '#231CAD',
    950: '#17126E',
  },
  cyan: {
    50: '#ECFEFF',
    100: '#CFFAFE',
    300: '#67E8F9',
    400: '#22D3EE',
    500: '#06B6D4',
    600: '#0891B2',
    700: '#0E7490',
    800: '#155E75',
    900: '#164E63',
  },
  neutral: {
    0: '#FFFFFF',
    50: '#F8FAFC',
    100: '#F1F5F9',
    200: '#E2E8F0',
    300: '#CBD5E1',
    400: '#94A3B8',
    500: '#64748B',
    600: '#475569',
    700: '#334155',
    800: '#1E293B',
    900: '#0F172A',
    950: '#020617',
  },
  success: {
    50: '#ECFDF5',
    100: '#D1FAE5',
    300: '#6EE7B7',
    400: '#34D399',
    500: '#10B981',
    600: '#059669',
    700: '#047857',
    800: '#065F46',
    900: '#064E3B',
  },
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    300: '#FCD34D',
    400: '#FBBF24',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309',
    800: '#92400E',
    900: '#78350F',
  },
  error: {
    50: '#FEF2F2',
    100: '#FEE2E2',
    300: '#FCA5A5',
    400: '#F87171',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
    800: '#991B1B',
    900: '#7F1D1D',
  },
  nav: '#0D1126',
} as const

export const lightSemantic = {
  bg: {
    primary: colors.neutral[0],
    secondary: colors.neutral[50],
    tertiary: colors.neutral[100],
    elevated: colors.neutral[0],
    muted: colors.neutral[100],
    inverse: colors.neutral[950],
    nav: colors.nav,
    card: colors.neutral[0],
    page: colors.neutral[50],
  },
  text: {
    primary: colors.neutral[900],
    secondary: colors.neutral[500],
    tertiary: colors.neutral[400],
    disabled: colors.neutral[300],
    inverse: colors.neutral[50],
    link: colors.primary[600],
    onDark: colors.neutral[0],
  },
  border: {
    default: colors.neutral[200],
    focus: colors.primary[600],
    error: colors.error[500],
    strong: colors.neutral[300],
  },
  accent: {
    default: colors.primary[600],
    hover: colors.primary[700],
    pressed: colors.primary[800],
    subtle: colors.primary[50],
    muted: colors.primary[100],
    alt: colors.cyan[500],
    altSubtle: colors.cyan[50],
    tertiary: colors.success[500],
    tertiarySubtle: colors.success[50],
  },
  chart: {
    primary: colors.primary[600],
    secondary: colors.cyan[600],
    tertiary: colors.success[600],
    track: colors.neutral[200],
  },
  status: {
    success: colors.success[500],
    successBg: colors.success[50],
    successBorder: colors.success[100],
    warning: colors.warning[500],
    warningBg: colors.warning[50],
    warningBorder: colors.warning[100],
    error: colors.error[500],
    errorBg: colors.error[50],
    errorBorder: colors.error[100],
  },
} as const

export const darkSemantic = {
  bg: {
    primary: colors.neutral[950],
    secondary: colors.neutral[900],
    tertiary: colors.neutral[800],
    elevated: colors.neutral[900],
    muted: colors.neutral[900],
    inverse: colors.neutral[0],
    nav: colors.neutral[950],
    card: colors.neutral[900],
    page: colors.neutral[950],
  },
  text: {
    primary: colors.neutral[50],
    secondary: colors.neutral[400],
    tertiary: colors.neutral[500],
    disabled: colors.neutral[600],
    inverse: colors.neutral[950],
    link: colors.primary[400],
    onDark: colors.neutral[0],
  },
  border: {
    default: colors.neutral[800],
    focus: colors.primary[400],
    error: colors.error[400],
    strong: colors.neutral[700],
  },
  accent: {
    default: colors.primary[400],
    hover: colors.primary[300],
    pressed: colors.primary[500],
    subtle: 'rgba(118,111,255,0.16)',
    muted: 'rgba(118,111,255,0.24)',
    alt: colors.cyan[400],
    altSubtle: 'rgba(34,211,238,0.14)',
    tertiary: colors.success[400],
    tertiarySubtle: 'rgba(52,211,153,0.14)',
  },
  chart: {
    primary: colors.primary[400],
    secondary: colors.cyan[400],
    tertiary: colors.success[400],
    track: 'rgba(255,255,255,0.10)',
  },
  status: {
    success: colors.success[500],
    successBg: 'rgba(16,185,129,0.14)',
    successBorder: 'rgba(16,185,129,0.24)',
    warning: colors.warning[500],
    warningBg: 'rgba(245,158,11,0.14)',
    warningBorder: 'rgba(245,158,11,0.26)',
    error: colors.error[400],
    errorBg: 'rgba(248,113,113,0.14)',
    errorBorder: 'rgba(248,113,113,0.26)',
  },
} as const

export interface SemanticTokens {
  bg: {
    primary: string
    secondary: string
    tertiary: string
    elevated: string
    muted: string
    inverse: string
    nav: string
    card: string
    page: string
  }
  text: {
    primary: string
    secondary: string
    tertiary: string
    disabled: string
    inverse: string
    link: string
    onDark: string
  }
  border: { default: string; focus: string; error: string; strong: string }
  accent: {
    default: string
    hover: string
    pressed: string
    subtle: string
    muted: string
    alt: string
    altSubtle: string
    tertiary: string
    tertiarySubtle: string
  }
  chart: { primary: string; secondary: string; tertiary: string; track: string }
  status: {
    success: string
    successBg: string
    successBorder: string
    warning: string
    warningBg: string
    warningBorder: string
    error: string
    errorBg: string
    errorBorder: string
  }
}

export const spacing = {
  0: 0,
  1: 4,
  1.5: 6,
  2: 8,
  3: 12,
  4: 16,
  5: 20,
  6: 24,
  7: 28,
  8: 32,
  10: 40,
  12: 48,
  16: 64,
  20: 80,
} as const

export const sizes = {
  icon: 34,
  avatarSm: 46,
  avatarMd: 52,
  avatarLg: 58,
} as const

// Ancho minimo de viewport para el layout de sidebar fijo en web (ver useIsDesktopLayout).
export const breakpoints = {
  desktop: 900,
} as const

// Ancho maximo de contenido centrado en las secciones de la landing/marketing (ver PlansSection).
export const layout = {
  contentMaxWidth: 1180,
} as const

export const radius = {
  none: 0,
  xs: 4,
  sm: 6,
  md: 8,
  lg: 12,
  xl: 16,
  '2xl': 20,
  full: 9999,
} as const

export const typography = {
  fontFamily: {
    sans: 'System',
    mono: 'Courier',
  },
  size: {
    xs: 11,
    sm: 13,
    base: 15,
    md: 16,
    lg: 18,
    xl: 20,
    '2xl': 24,
    '3xl': 30,
    '4xl': 36,
  },
  weight: {
    regular: '400' as const,
    medium: '500' as const,
    semibold: '600' as const,
    bold: '700' as const,
  },
  lineHeight: {
    tight: 1.2,
    normal: 1.5,
    relaxed: 1.75,
  },
} as const

export const shadow: Record<'sm' | 'md' | 'lg' | 'xl', ShadowStyle> = {
  sm: { boxShadow: '0 1px 2px rgba(15,23,42,0.05)' },
  md: { boxShadow: '0 8px 18px rgba(15,23,42,0.07)' },
  lg: { boxShadow: '0 14px 32px rgba(15,23,42,0.10)' },
  xl: { boxShadow: '0 20px 48px rgba(15,23,42,0.12)' },
}

// Colores para superficies siempre oscuras (nav, cards highlighted, dark inputs)
// Estos valores son independientes del tema light/dark de la app
export const overlay = {
  text: {
    primary: 'rgba(255,255,255,1.00)',
    muted: 'rgba(255,255,255,0.70)',
    subtle: 'rgba(255,255,255,0.50)',
    faint: 'rgba(255,255,255,0.35)',
    ghost: 'rgba(255,255,255,0.20)',
    placeholder: 'rgba(255,255,255,0.30)',
    icon: 'rgba(255,255,255,0.35)',
    label: 'rgba(255,255,255,0.55)',
  },
  border: {
    default: 'rgba(255,255,255,0.08)',
    hover: 'rgba(255,255,255,0.10)',
    strong: 'rgba(255,255,255,0.15)',
  },
  surface: {
    default: 'rgba(255,255,255,0.06)',
    hover: 'rgba(255,255,255,0.09)',
    badge: 'rgba(255,255,255,0.20)',
    backdrop: 'rgba(9,9,11,0.45)',
  },
} as const

export const animation = {
  duration: {
    fast: 150,
    normal: 250,
    slow: 400,
  },
} as const

// Identidad visual del logo Wali ("W" de doble trazo morado/tinta sobre fondo plano)
export const brand = {
  accent: colors.primary[600],
  surface: {
    light: '#F7F8FC',
    dark: '#0D1126',
  },
  ink: {
    light: '#0D1126',
    dark: colors.neutral[0],
  },
} as const
