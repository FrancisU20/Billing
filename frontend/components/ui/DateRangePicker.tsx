import React, { useMemo, useState } from 'react'
import { Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { Button } from '@/components/ui/Button'
import { radius, spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'
import { ecuadorTodayISO } from '@/lib/utils/ecuador-time'
import { formatDateRangeLabel } from '@/lib/utils/format'
import {
  calendarDaysForMonth,
  isDateInRange,
  monthLabel,
  monthRange,
  normalizeDateRange,
  selectDateInRange,
  shiftMonth,
  validDateOnly,
  weekRange,
  type DateRangeEdge,
  type DateRangeValue,
} from '@/lib/utils/date-range'

interface DateRangePickerProps {
  from: string
  to: string
  placeholder?: string
  onChange: (value: DateRangeValue) => void
}

const WEEKDAYS = ['L', 'M', 'M', 'J', 'V', 'S', 'D']

export function DateRangePicker({
  from,
  to,
  placeholder = 'Seleccionar rango',
  onChange,
}: DateRangePickerProps) {
  const { semantic } = useTheme()
  const initialMonth = validDateOnly(from) ? from : validDateOnly(to) ? to : ecuadorTodayISO()
  const [visible, setVisible] = useState(false)
  const [draft, setDraft] = useState<DateRangeValue>({ from, to })
  const [activeEdge, setActiveEdge] = useState<DateRangeEdge>('from')
  const [month, setMonth] = useState(initialMonth)
  const days = useMemo(() => calendarDaysForMonth(month), [month])
  const normalized = normalizeDateRange(draft)
  const label = from || to ? formatDateRangeLabel(from, to) : placeholder

  function open() {
    const currentMonth = validDateOnly(from) ? from : validDateOnly(to) ? to : ecuadorTodayISO()
    setDraft({ from, to })
    setActiveEdge(from && !to ? 'to' : 'from')
    setMonth(currentMonth)
    setVisible(true)
  }

  function close() {
    setVisible(false)
  }

  function apply() {
    onChange(normalizeDateRange(draft))
    setVisible(false)
  }

  function selectPreset(next: DateRangeValue) {
    setDraft(next)
    if (next.from) setMonth(next.from)
  }

  function selectDay(date: string) {
    const next = selectDateInRange(draft, date, activeEdge)
    setDraft(next)
    setActiveEdge(activeEdge === 'from' ? 'to' : 'from')
  }

  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Seleccionar rango de fechas"
        onPress={open}
        style={({ pressed }) => [
          styles.trigger,
          {
            backgroundColor: pressed ? semantic.bg.secondary : semantic.bg.primary,
            borderColor: semantic.border.default,
          },
        ]}
      >
        <Ionicons name="calendar-outline" size={18} color={semantic.text.tertiary} />
        <Text
          numberOfLines={1}
          style={[
            styles.triggerText,
            { color: from || to ? semantic.text.primary : semantic.text.tertiary },
          ]}
        >
          {label}
        </Text>
      </Pressable>

      <Modal transparent visible={visible} animationType="fade" onRequestClose={close}>
        <View style={styles.overlay}>
          <Pressable style={StyleSheet.absoluteFill} onPress={close} />
          <View
            style={[
              styles.dialog,
              { backgroundColor: semantic.bg.card, borderColor: semantic.border.default },
            ]}
          >
            <View style={styles.header}>
              <View>
                <Text style={[styles.title, { color: semantic.text.primary }]}>
                  Rango de fechas
                </Text>
                <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
                  {normalized.from || normalized.to
                    ? formatDateRangeLabel(normalized.from, normalized.to)
                    : 'Sin fechas seleccionadas'}
                </Text>
              </View>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Cerrar calendario"
                hitSlop={8}
                onPress={close}
              >
                <Ionicons name="close-outline" size={22} color={semantic.text.secondary} />
              </Pressable>
            </View>

            <View style={styles.presets}>
              <PresetButton label="Hoy" onPress={() => selectPreset(todayRange())} />
              <PresetButton label="Esta semana" onPress={() => selectPreset(weekRange())} />
              <PresetButton label="Este mes" onPress={() => selectPreset(monthRange())} />
              <PresetButton label="Limpiar" onPress={() => selectPreset({ from: '', to: '' })} />
            </View>

            <View style={styles.rangeRow}>
              <RangeSideButton
                label="Desde"
                value={normalized.from || 'Sin definir'}
                selected={activeEdge === 'from'}
                onPress={() => setActiveEdge('from')}
              />
              <RangeSideButton
                label="Hasta"
                value={normalized.to || 'Sin definir'}
                selected={activeEdge === 'to'}
                onPress={() => setActiveEdge('to')}
              />
            </View>

            <View style={styles.monthHeader}>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Mes anterior"
                hitSlop={8}
                onPress={() => setMonth((current) => shiftMonth(current, -1))}
              >
                <Ionicons name="chevron-back-outline" size={22} color={semantic.text.secondary} />
              </Pressable>
              <Text style={[styles.monthLabel, { color: semantic.text.primary }]}>
                {capitalize(monthLabel(month))}
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityLabel="Mes siguiente"
                hitSlop={8}
                onPress={() => setMonth((current) => shiftMonth(current, 1))}
              >
                <Ionicons
                  name="chevron-forward-outline"
                  size={22}
                  color={semantic.text.secondary}
                />
              </Pressable>
            </View>

            <View style={styles.weekHeader}>
              {WEEKDAYS.map((day) => (
                <Text key={day} style={[styles.weekday, { color: semantic.text.tertiary }]}>
                  {day}
                </Text>
              ))}
            </View>

            <View style={styles.daysGrid}>
              {days.map((day) => {
                const isStart = normalized.from === day.iso
                const isEnd = normalized.to === day.iso
                const isInside = isDateInRange(day.iso, normalized)
                const isSelected = isStart || isEnd
                return (
                  <Pressable
                    key={day.iso}
                    accessibilityRole="button"
                    accessibilityLabel={`Seleccionar ${day.iso}`}
                    onPress={() => selectDay(day.iso)}
                    style={[
                      styles.day,
                      {
                        backgroundColor: isSelected
                          ? semantic.accent.default
                          : isInside
                            ? semantic.accent.subtle
                            : 'transparent',
                      },
                    ]}
                  >
                    <Text
                      style={[
                        styles.dayText,
                        {
                          color: isSelected
                            ? semantic.text.onDark
                            : day.inCurrentMonth
                              ? semantic.text.primary
                              : semantic.text.disabled,
                          fontWeight: isSelected
                            ? typography.weight.bold
                            : typography.weight.medium,
                        },
                      ]}
                    >
                      {day.day}
                    </Text>
                  </Pressable>
                )
              })}
            </View>

            <View style={styles.actions}>
              <Button variant="outline" size="md" onPress={close}>
                Cancelar
              </Button>
              <Button variant="primary" size="md" onPress={apply}>
                Listo
              </Button>
            </View>
          </View>
        </View>
      </Modal>
    </>
  )
}

function todayRange(): DateRangeValue {
  const today = ecuadorTodayISO()
  return { from: today, to: today }
}

function capitalize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

interface PresetButtonProps {
  label: string
  onPress: () => void
}

function PresetButton({ label, onPress }: PresetButtonProps) {
  const { semantic } = useTheme()
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={({ pressed }) => [
        styles.preset,
        {
          backgroundColor: pressed ? semantic.accent.subtle : semantic.bg.secondary,
          borderColor: semantic.border.default,
        },
      ]}
    >
      <Text style={[styles.presetText, { color: semantic.text.primary }]}>{label}</Text>
    </Pressable>
  )
}

interface RangeSideButtonProps {
  label: string
  value: string
  selected: boolean
  onPress: () => void
}

function RangeSideButton({ label, value, selected, onPress }: RangeSideButtonProps) {
  const { semantic } = useTheme()
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      style={[
        styles.rangeSide,
        {
          backgroundColor: selected ? semantic.accent.subtle : semantic.bg.secondary,
          borderColor: selected ? semantic.accent.default : semantic.border.default,
        },
      ]}
    >
      <Text style={[styles.rangeLabel, { color: semantic.text.tertiary }]}>{label}</Text>
      <Text style={[styles.rangeValue, { color: semantic.text.primary }]}>{value}</Text>
    </Pressable>
  )
}

const styles = StyleSheet.create({
  trigger: {
    alignItems: 'center',
    borderRadius: radius.md,
    borderWidth: 1,
    flexDirection: 'row',
    gap: spacing[3],
    minHeight: 52,
    minWidth: 260,
    paddingHorizontal: spacing[4],
  },
  triggerText: {
    flex: 1,
    fontSize: typography.size.base,
    fontWeight: typography.weight.medium,
    includeFontPadding: false,
  },
  overlay: {
    alignItems: 'center',
    backgroundColor: 'rgba(15, 23, 42, 0.46)',
    flex: 1,
    justifyContent: 'center',
    padding: spacing[4],
  },
  dialog: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    maxWidth: 430,
    padding: spacing[5],
    width: '100%',
  },
  header: {
    alignItems: 'flex-start',
    flexDirection: 'row',
    gap: spacing[3],
    justifyContent: 'space-between',
  },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  subtitle: { fontSize: typography.size.sm, lineHeight: typography.size.sm * 1.4, marginTop: 2 },
  presets: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  preset: {
    borderRadius: radius.sm,
    borderWidth: 1,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  presetText: { fontSize: typography.size.sm, fontWeight: typography.weight.semibold },
  rangeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[2] },
  rangeSide: {
    borderRadius: radius.md,
    borderWidth: 1,
    flex: 1,
    gap: 2,
    minWidth: 150,
    paddingHorizontal: spacing[3],
    paddingVertical: spacing[2],
  },
  rangeLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
  rangeValue: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  monthHeader: {
    alignItems: 'center',
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  monthLabel: { fontSize: typography.size.base, fontWeight: typography.weight.bold },
  weekHeader: { flexDirection: 'row' },
  weekday: {
    flex: 1,
    fontSize: typography.size.xs,
    fontWeight: typography.weight.bold,
    textAlign: 'center',
  },
  daysGrid: { flexDirection: 'row', flexWrap: 'wrap' },
  day: {
    alignItems: 'center',
    aspectRatio: 1,
    borderRadius: radius.sm,
    justifyContent: 'center',
    width: `${100 / 7}%`,
  },
  dayText: { fontSize: typography.size.sm, includeFontPadding: false },
  actions: { flexDirection: 'row', gap: spacing[2], justifyContent: 'flex-end' },
})
