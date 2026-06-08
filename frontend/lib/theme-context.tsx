import React, { createContext, useContext } from 'react'
import { useColorScheme } from 'react-native'
import { lightSemantic, darkSemantic, type SemanticTokens } from '@/constants/tokens'

interface ThemeContextValue {
  semantic: SemanticTokens
  isDark: boolean
  colorScheme: 'light' | 'dark'
}

const ThemeContext = createContext<ThemeContextValue>({
  semantic: lightSemantic,
  isDark: false,
  colorScheme: 'light',
})

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const scheme = useColorScheme()
  const isDark = scheme === 'dark'

  return (
    <ThemeContext.Provider
      value={{
        semantic: isDark ? darkSemantic : lightSemantic,
        isDark,
        colorScheme: isDark ? 'dark' : 'light',
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme(): ThemeContextValue {
  return useContext(ThemeContext)
}
