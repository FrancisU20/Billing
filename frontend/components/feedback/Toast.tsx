import React, { createContext, useCallback, useContext, useRef, useState } from 'react'
import { Animated, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { typography, radius, spacing, shadow } from '@/constants/tokens'

type ToastVariant = 'success' | 'error' | 'warning' | 'info'

interface ToastMessage {
  id: string
  message: string
  variant: ToastVariant
}

interface ToastContextValue {
  show: (message: string, variant?: ToastVariant) => void
  success: (message: string) => void
  error: (message: string) => void
  warning: (message: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

function ToastItem({ item, onDone }: { item: ToastMessage; onDone: (id: string) => void }) {
  const { semantic } = useTheme()
  const opacity = useRef(new Animated.Value(0)).current

  const variantMap: Record<
    ToastVariant,
    { icon: keyof typeof Ionicons.glyphMap; color: string; bg: string }
  > = {
    success: {
      icon: 'checkmark-circle',
      color: semantic.status.success,
      bg: semantic.status.successBg,
    },
    error: { icon: 'alert-circle', color: semantic.status.error, bg: semantic.status.errorBg },
    warning: { icon: 'warning', color: semantic.status.warning, bg: semantic.status.warningBg },
    info: {
      icon: 'information-circle',
      color: semantic.accent.default,
      bg: semantic.accent.subtle,
    },
  }

  const { icon, color, bg } = variantMap[item.variant]

  React.useEffect(() => {
    Animated.sequence([
      Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
      Animated.delay(2800),
      Animated.timing(opacity, { toValue: 0, duration: 300, useNativeDriver: true }),
    ]).start(() => onDone(item.id))
  }, [item.id, onDone, opacity])

  return (
    <Animated.View style={[staticStyles.toast, { opacity, backgroundColor: bg }]}>
      <Ionicons name={icon} size={18} color={color} />
      <Text style={[staticStyles.message, { color }]}>{item.message}</Text>
    </Animated.View>
  )
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastMessage[]>([])

  const show = useCallback((message: string, variant: ToastVariant = 'info') => {
    const id = Date.now().toString()
    setToasts((prev) => [...prev.slice(-2), { id, message, variant }])
  }, [])

  const remove = useCallback((id: string) => setToasts((p) => p.filter((t) => t.id !== id)), [])

  const ctx: ToastContextValue = {
    show,
    success: (m) => show(m, 'success'),
    error: (m) => show(m, 'error'),
    warning: (m) => show(m, 'warning'),
  }

  return (
    <ToastContext.Provider value={ctx}>
      {children}
      <View style={[staticStyles.container, { pointerEvents: 'none' }]}>
        {toasts.map((t) => (
          <ToastItem key={t.id} item={t} onDone={remove} />
        ))}
      </View>
    </ToastContext.Provider>
  )
}

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) throw new Error('useToast must be used inside ToastProvider')
  return ctx
}

const staticStyles = StyleSheet.create({
  container: {
    position: 'absolute',
    bottom: 80,
    left: spacing[4],
    right: spacing[4],
    gap: spacing[2],
    zIndex: 9999,
  },
  toast: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: spacing[2] + 2,
    paddingHorizontal: spacing[4],
    paddingVertical: spacing[3],
    borderRadius: radius.lg,
    ...shadow.md,
  },
  message: { flex: 1, fontSize: typography.size.sm, fontWeight: typography.weight.medium },
})
