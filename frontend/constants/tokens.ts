export const colors = {
  primary: {
    50: '#EEF2FF',
    100: '#E0E7FF',
    200: '#C7D2FE',
    300: '#A5B4FC',
    400: '#818CF8',
    500: '#6366F1',
    600: '#4F46E5',
    700: '#4338CA',
    800: '#3730A3',
    900: '#312E81',
    950: '#1E1B4B',
  },
  cyan: {
    50: '#ECFEFF',
    100: '#CFFAFE',
    400: '#22D3EE',
    500: '#06B6D4',
    600: '#0891B2',
    700: '#0E7490',
  },
  teal: {
    50: '#F0FDFA',
    100: '#CCFBF1',
    400: '#2DD4BF',
    500: '#14B8A6',
    600: '#0D9488',
    700: '#0F766E',
  },
  neutral: {
    0: '#FFFFFF',
    50: '#FAFAFA',
    100: '#F4F4F5',
    200: '#E4E4E7',
    300: '#D4D4D8',
    400: '#A1A1AA',
    500: '#71717A',
    600: '#52525B',
    700: '#3F3F46',
    800: '#27272A',
    900: '#18181B',
    950: '#09090B',
  },
  success: {
    50: '#F0FDF4',
    100: '#DCFCE7',
    500: '#22C55E',
    600: '#16A34A',
    700: '#15803D',
  },
  warning: {
    50: '#FFFBEB',
    100: '#FEF3C7',
    500: '#F59E0B',
    600: '#D97706',
    700: '#B45309',
  },
  error: {
    50: '#FFF1F2',
    100: '#FFE4E6',
    400: '#F87171',
    500: '#EF4444',
    600: '#DC2626',
    700: '#B91C1C',
  },
  nav: '#09090B',
} as const

export const lightSemantic = {
  bg: {
    primary: colors.neutral[0],
    secondary: colors.neutral[50],
    tertiary: colors.neutral[100],
    elevated: colors.neutral[0],
    muted: '#F8FAFC',
    inverse: colors.neutral[950],
    nav: colors.nav,
    card: colors.neutral[0],
    page: '#F5F5F7',
  },
  text: {
    primary: colors.neutral[950],
    secondary: colors.neutral[500],
    tertiary: colors.neutral[400],
    disabled: colors.neutral[300],
    inverse: colors.neutral[0],
    link: colors.primary[600],
    onDark: colors.neutral[0],
  },
  border: {
    default: colors.neutral[200],
    focus: colors.primary[500],
    error: colors.error[500],
    strong: colors.neutral[300],
  },
  accent: {
    default: colors.primary[500],
    hover: colors.primary[600],
    pressed: colors.primary[700],
    subtle: colors.primary[50],
    muted: colors.primary[100],
    alt: colors.cyan[600],
    altSubtle: colors.cyan[50],
    tertiary: colors.teal[600],
    tertiarySubtle: colors.teal[50],
  },
  chart: {
    primary: colors.primary[600],
    secondary: colors.cyan[600],
    tertiary: colors.teal[600],
    track: colors.neutral[200],
  },
  status: {
    success: colors.success[500],
    successBg: colors.success[50],
    warning: colors.warning[500],
    warningBg: colors.warning[50],
    error: colors.error[500],
    errorBg: colors.error[50],
  },
} as const

export const darkSemantic = {
  bg: {
    primary: '#0A0A0B',
    secondary: '#111113',
    tertiary: '#1C1C1F',
    elevated: '#18181B',
    muted: '#101114',
    inverse: colors.neutral[0],
    nav: '#000000',
    card: '#18181B',
    page: '#000000',
  },
  text: {
    primary: colors.neutral[50],
    secondary: colors.neutral[400],
    tertiary: colors.neutral[600],
    disabled: colors.neutral[700],
    inverse: colors.neutral[950],
    link: colors.primary[400],
    onDark: colors.neutral[0],
  },
  border: {
    default: 'rgba(255,255,255,0.08)',
    focus: colors.primary[400],
    error: colors.error[400],
    strong: 'rgba(255,255,255,0.15)',
  },
  accent: {
    default: colors.primary[400],
    hover: colors.primary[300],
    pressed: colors.primary[500],
    subtle: 'rgba(99,102,241,0.15)',
    muted: 'rgba(99,102,241,0.25)',
    alt: colors.cyan[400],
    altSubtle: 'rgba(34,211,238,0.14)',
    tertiary: colors.teal[400],
    tertiarySubtle: 'rgba(45,212,191,0.14)',
  },
  chart: {
    primary: colors.primary[400],
    secondary: colors.cyan[400],
    tertiary: colors.teal[400],
    track: 'rgba(255,255,255,0.10)',
  },
  status: {
    success: colors.success[500],
    successBg: 'rgba(34,197,94,0.12)',
    warning: colors.warning[500],
    warningBg: 'rgba(245,158,11,0.12)',
    error: colors.error[400],
    errorBg: 'rgba(239,68,68,0.12)',
  },
} as const

// Alias para imports legacy (componentes migrados usan useTheme en su lugar)
export const semantic = lightSemantic

export interface SemanticTokens {
  bg: { primary: string; secondary: string; tertiary: string; elevated: string; muted: string; inverse: string; nav: string; card: string; page: string }
  text: { primary: string; secondary: string; tertiary: string; disabled: string; inverse: string; link: string; onDark: string }
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
  status: { success: string; successBg: string; warning: string; warningBg: string; error: string; errorBg: string }
}

export const spacing = {
  0: 0,
  1: 4,
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

export const shadow = {
  sm: {
    boxShadow: '0 1px 2px rgba(9,9,11,0.05)',
  },
  md: {
    boxShadow: '0 4px 8px rgba(9,9,11,0.08)',
  },
  lg: {
    boxShadow: '0 8px 16px rgba(9,9,11,0.12)',
  },
  xl: {
    boxShadow: '0 16px 40px rgba(9,9,11,0.14)',
  },
} as const

// Colores para superficies siempre oscuras (nav, cards highlighted, dark inputs)
// Estos valores son independientes del tema light/dark de la app
export const overlay = {
  text: {
    primary:     'rgba(255,255,255,1.00)',
    muted:       'rgba(255,255,255,0.70)',
    subtle:      'rgba(255,255,255,0.50)',
    faint:       'rgba(255,255,255,0.35)',
    ghost:       'rgba(255,255,255,0.20)',
    placeholder: 'rgba(255,255,255,0.30)',
    icon:        'rgba(255,255,255,0.35)',
    label:       'rgba(255,255,255,0.55)',
  },
  border: {
    default: 'rgba(255,255,255,0.08)',
    hover:   'rgba(255,255,255,0.10)',
    strong:  'rgba(255,255,255,0.15)',
  },
  surface: {
    default: 'rgba(255,255,255,0.06)',
    hover:   'rgba(255,255,255,0.09)',
    badge:   'rgba(255,255,255,0.20)',
  },
} as const

export const animation = {
  duration: {
    fast: 150,
    normal: 250,
    slow: 400,
  },
} as const
