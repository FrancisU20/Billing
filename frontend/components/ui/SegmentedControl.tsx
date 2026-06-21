import React from 'react'
import { Pressable, StyleSheet, Text, View, type ViewStyle } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'

interface SegmentedOption<T extends string> {
  value: T
  label: string
}

interface SegmentedControlProps<T extends string> {
  options: ReadonlyArray<SegmentedOption<T>>
  value: T
  onChange: (value: T) => void
  /** Estira el control y reparte el ancho disponible en partes iguales entre las
   * opciones — usar en paneles de filtros donde el control es el unico elemento de su
   * fila/columna. Default `false` (ancho segun contenido) para usos inline en
   * formularios, donde estirar veria forzado. */
  stretch?: boolean
  /** Fuerza N opciones por fila via `minWidth` porcentual, en vez de dejar que el
   * contenido de cada opcion decida donde envuelve (con `flexWrap` solo, opciones
   * cortas como "RUC"/"Cédula" caben 3 en la primera fila y la 4ta queda sola). Usar
   * junto a `stretch` cuando se necesita una grilla pareja (ej. 2x2 con 4 opciones). */
  columns?: number
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  stretch = false,
  columns,
}: SegmentedControlProps<T>) {
  const { semantic } = useTheme()
  // -2% de margen para que el gap entre opciones no empuje a una columna de menos.
  const columnWidth: ViewStyle | null = columns
    ? { minWidth: `${100 / columns - 2}%` as ViewStyle['minWidth'] }
    : null

  return (
    <View
      style={[
        styles.container,
        stretch && styles.containerStretch,
        { backgroundColor: semantic.bg.tertiary },
      ]}
    >
      {options.map((option) => {
        const selected = option.value === value
        return (
          <Pressable
            key={option.value}
            onPress={() => onChange(option.value)}
            style={({ pressed }) => [
              styles.option,
              stretch && styles.optionStretch,
              columnWidth,
              {
                backgroundColor: selected
                  ? semantic.bg.elevated
                  : pressed
                    ? semantic.bg.secondary
                    : 'transparent',
                borderColor: selected ? semantic.border.default : 'transparent',
              },
            ]}
          >
            <Text
              style={[
                styles.label,
                { color: selected ? semantic.text.primary : semantic.text.secondary },
              ]}
              numberOfLines={1}
            >
              {option.label}
            </Text>
          </Pressable>
        )
      })}
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    alignSelf: 'flex-start',
    borderRadius: radius.md,
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: spacing[1],
    padding: spacing[1],
  },
  containerStretch: { alignSelf: 'stretch' },
  option: {
    alignItems: 'center',
    borderRadius: radius.sm,
    borderWidth: 1,
    justifyContent: 'center',
    minHeight: 34,
    minWidth: 88,
    paddingHorizontal: spacing[3],
  },
  optionStretch: { flex: 1 },
  label: {
    fontSize: typography.size.sm,
    fontWeight: typography.weight.semibold,
    includeFontPadding: false,
  },
})
