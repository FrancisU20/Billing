import React, { useMemo, useState } from 'react'
import { Pressable, StyleSheet, Text, View, type TextInputProps } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { Input } from './Input'

type DiscountMode = 'amount' | 'percent'

interface DiscountInputProps extends Omit<TextInputProps, 'value' | 'onChangeText'> {
  label: string
  value: string
  baseAmount: number
  onChangeText: (value: string) => void
  error?: string
  hint?: string
}

function parseNumber(value: string): number {
  const normalized = value.replace(',', '.').replace(/[^0-9.]/g, '')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

function formatMoney(value: number): string {
  return Math.max(0, Math.round(value * 100) / 100).toFixed(2)
}

function formatPercent(value: number): string {
  return Math.max(0, Math.round(value * 100) / 100).toFixed(2)
}

export function DiscountInput({
  label,
  value,
  baseAmount,
  onChangeText,
  error,
  hint,
  ...inputProps
}: DiscountInputProps) {
  const { semantic } = useTheme()
  const [mode, setMode] = useState<DiscountMode>('amount')

  const percentValue = useMemo(() => {
    if (baseAmount <= 0) return '0'
    return formatPercent((parseNumber(value) / baseAmount) * 100)
  }, [baseAmount, value])

  const visibleValue = mode === 'amount' ? value : `${percentValue}%`

  function changeMode(next: DiscountMode) {
    if (next === mode) return
    if (next === 'amount') {
      onChangeText(formatMoney((baseAmount * parseNumber(percentValue)) / 100))
    }
    setMode(next)
  }

  function changeValue(next: string) {
    if (mode === 'amount') {
      onChangeText(next)
      return
    }
    const percent = Math.min(parseNumber(next), 100)
    onChangeText(formatMoney((baseAmount * percent) / 100))
  }

  return (
    <View style={styles.container}>
      <View style={styles.labelRow}>
        <Text style={[styles.label, { color: semantic.text.primary }]}>{label}</Text>
      </View>
      <Input
        {...inputProps}
        value={visibleValue}
        onChangeText={changeValue}
        hasError={!!error}
        leftIcon="pricetag-outline"
        rightElement={
          <View style={[styles.switcher, { backgroundColor: semantic.bg.secondary }]}>
            <ModeButton
              label="$"
              selected={mode === 'amount'}
              onPress={() => changeMode('amount')}
            />
            <ModeButton
              label="%"
              selected={mode === 'percent'}
              onPress={() => changeMode('percent')}
            />
          </View>
        }
      />
      {error ? (
        <View style={styles.feedbackRow}>
          <Ionicons name="alert-circle-outline" size={13} color={semantic.status.error} />
          <Text style={[styles.feedbackText, { color: semantic.status.error }]}>{error}</Text>
        </View>
      ) : hint ? (
        <Text style={[styles.feedbackText, { color: semantic.text.secondary }]}>{hint}</Text>
      ) : null}
    </View>
  )
}

function ModeButton({
  label,
  selected,
  onPress,
}: {
  label: string
  selected: boolean
  onPress: () => void
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={`Descuento en ${label === '$' ? 'valor' : 'porcentaje'}`}
      onPress={onPress}
      style={[
        styles.modeButton,
        { backgroundColor: selected ? semantic.accent.default : 'transparent' },
      ]}
    >
      <Text
        style={[styles.modeLabel, { color: selected ? semantic.bg.card : semantic.text.secondary }]}
      >
        {label}
      </Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  container: { gap: spacing[1] + 2 },
  labelRow: { flexDirection: 'row', alignItems: 'center' },
  label: { fontSize: typography.size.sm, fontWeight: typography.weight.medium },
  switcher: {
    borderRadius: radius.sm,
    flexDirection: 'row',
    gap: spacing[1] - 2,
    padding: 2,
  },
  modeButton: {
    alignItems: 'center',
    borderRadius: radius.sm,
    height: 28,
    justifyContent: 'center',
    width: 28,
  },
  modeLabel: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  feedbackRow: { flexDirection: 'row', alignItems: 'center', gap: spacing[1] },
  feedbackText: { fontSize: typography.size.xs },
})
