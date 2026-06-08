import React from 'react'
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
  type ViewProps,
} from 'react-native'
import { SafeAreaView } from 'react-native-safe-area-context'
import { useTheme } from '@/lib/theme-context'
import { spacing } from '@/constants/tokens'

interface ScreenProps extends ViewProps {
  children: React.ReactNode
  scrollable?: boolean
  padded?: boolean
  centered?: boolean
  keyboardAware?: boolean
}

export function Screen({
  children,
  scrollable = false,
  padded = true,
  centered = false,
  keyboardAware = false,
  style,
  ...props
}: ScreenProps) {
  const { semantic } = useTheme()

  const bg = { backgroundColor: semantic.bg.primary }

  const content = scrollable ? (
    <ScrollView
      style={[staticStyles.fill, bg]}
      contentContainerStyle={[padded && staticStyles.padded, centered && staticStyles.centered]}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}
    >
      {children}
    </ScrollView>
  ) : (
    <View
      {...props}
      style={[
        staticStyles.fill,
        bg,
        padded && staticStyles.padded,
        centered && staticStyles.centered,
        style,
      ]}
    >
      {children}
    </View>
  )

  return (
    <SafeAreaView style={[staticStyles.fill, bg]}>
      {keyboardAware ? (
        <KeyboardAvoidingView
          style={staticStyles.fill}
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        >
          {content}
        </KeyboardAvoidingView>
      ) : (
        content
      )}
    </SafeAreaView>
  )
}

const staticStyles = StyleSheet.create({
  fill: { flex: 1 },
  padded: { padding: spacing[5] },
  centered: { alignItems: 'center', justifyContent: 'center' },
})
