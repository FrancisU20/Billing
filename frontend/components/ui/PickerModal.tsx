import React from 'react'
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from 'react-native'
import { Ionicons } from '@expo/vector-icons'
import { ApiErrorBanner } from '@/components/ui/ApiErrorBanner'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SearchInput } from '@/components/ui/SearchInput'
import type { ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { overlay, radius, spacing, typography } from '@/constants/tokens'

interface PickerModalProps<T> {
  visible: boolean
  onClose: () => void
  title: string
  searchPlaceholder: string
  searchValue: string
  onSearchChangeText: (text: string) => void
  onSearchChange: (text: string) => void
  /** Enter en el input sigue disparando una busqueda inmediata — no hay boton "Buscar"
   * visible, la busqueda ya es reactiva mientras se escribe (ver `onSearchChange`). */
  onSearchSubmit: () => void
  searchLoading: boolean
  /** Boton(es) extra junto a la barra de busqueda (ej. "Añadir" en ProductPickerModal). */
  headerActions?: React.ReactNode
  error: ApiError | null
  results: T[]
  keyExtractor: (item: T) => string
  renderItem: (item: T) => React.ReactNode
  emptyState: React.ReactNode
  /** Slot extra debajo de la lista (ej. formulario de creacion rapida). */
  footer?: React.ReactNode
  maxDialogWidth?: number
  maxDialogHeightPct?: number
  listMaxHeight?: number
}

/**
 * Esqueleto compartido de los modales "buscar y seleccionar" (overlay+dialog+header con
 * cerrar+barra de busqueda+banner de error+lista con fila presionable+estado vacio
 * parametrizable). `ClientPickerModal`/`ProductPickerModal` lo envuelven con su propia
 * logica de busqueda (debounce+request-id) y contenido de fila.
 */
export function PickerModal<T>({
  visible,
  onClose,
  title,
  searchPlaceholder,
  searchValue,
  onSearchChangeText,
  onSearchChange,
  onSearchSubmit,
  searchLoading,
  headerActions,
  error,
  results,
  keyExtractor,
  renderItem,
  emptyState,
  footer,
  maxDialogWidth = 480,
  maxDialogHeightPct = 80,
  listMaxHeight = 320,
}: PickerModalProps<T>) {
  const { semantic } = useTheme()

  return (
    <Modal transparent visible={visible} animationType="fade" onRequestClose={onClose}>
      <View style={styles.overlay}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
        <View
          style={[
            styles.dialog,
            {
              backgroundColor: semantic.bg.card,
              borderColor: semantic.border.default,
              maxWidth: maxDialogWidth,
              maxHeight: `${maxDialogHeightPct}%`,
            },
          ]}
        >
          <View style={styles.header}>
            <Text style={[styles.title, { color: semantic.text.primary }]}>{title}</Text>
            <Pressable onPress={onClose} hitSlop={8} accessibilityLabel="Cerrar">
              <Ionicons name="close-outline" size={22} color={semantic.text.secondary} />
            </Pressable>
          </View>

          <View style={styles.searchRow}>
            <View style={styles.searchInput}>
              <SearchInput
                placeholder={searchPlaceholder}
                value={searchValue}
                onChangeText={onSearchChangeText}
                onSearchChange={onSearchChange}
                onSubmitEditing={onSearchSubmit}
                autoFocus
              />
            </View>
            {headerActions}
          </View>

          {error ? <ApiErrorBanner error={error} /> : null}

          {searchLoading ? (
            <LoadingSpinner compact label="Buscando..." />
          ) : (
            <FlatList
              data={results}
              keyExtractor={keyExtractor}
              style={{ maxHeight: listMaxHeight }}
              ListEmptyComponent={<View>{emptyState}</View>}
              renderItem={({ item }) => <View>{renderItem(item)}</View>}
            />
          )}

          {footer}
        </View>
      </View>
    </Modal>
  )
}

export function PickerResultRow({
  onPress,
  children,
}: {
  onPress: () => void
  children: React.ReactNode
}) {
  const { semantic } = useTheme()
  return (
    <Pressable
      onPress={onPress}
      style={({ pressed }) => [
        styles.resultRow,
        {
          backgroundColor: pressed ? semantic.bg.secondary : 'transparent',
          borderColor: semantic.border.default,
        },
      ]}
    >
      {children}
    </Pressable>
  )
}

const styles = StyleSheet.create({
  overlay: {
    alignItems: 'center',
    backgroundColor: overlay.surface.backdrop,
    flex: 1,
    justifyContent: 'center',
    padding: spacing[5],
  },
  dialog: {
    borderRadius: radius.md,
    borderWidth: 1,
    gap: spacing[4],
    padding: spacing[5],
    width: '100%',
  },
  header: { alignItems: 'center', flexDirection: 'row', justifyContent: 'space-between' },
  title: { fontSize: typography.size.lg, fontWeight: typography.weight.bold },
  searchRow: { flexDirection: 'row', gap: spacing[2] },
  searchInput: { flex: 1 },
  resultRow: { borderBottomWidth: 1, gap: spacing[1] - 2, padding: spacing[3] },
})
