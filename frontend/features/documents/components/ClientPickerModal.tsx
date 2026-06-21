import React, { useEffect, useRef, useState } from 'react'
import { StyleSheet, Text, View } from 'react-native'
import { Button } from '@/components/ui/Button'
import { FormField } from '@/components/ui/FormField'
import { PickerModal, PickerResultRow } from '@/components/ui/PickerModal'
import { SegmentedControl } from '@/components/ui/SegmentedControl'
import { EmailField, PhoneField } from '@/components/ui/SpecializedFields'
import { createIdempotencyKey } from '@/lib/api/idempotency'
import { toApiError, type ApiError } from '@/lib/api/errors'
import { useTheme } from '@/lib/theme-context'
import { radius, spacing, typography } from '@/constants/tokens'
import { clientsApi } from '@/features/clients/api'
import { CLIENT_IDENTIFICATION_OPTIONS, CLIENT_PERSON_OPTIONS } from '@/features/clients/constants'
import type { Client, IdentificationType, PersonType } from '@/features/clients/types'

interface ClientPickerModalProps {
  visible: boolean
  onClose: () => void
  onSelect: (client: Client) => void
}

export function ClientPickerModal({ visible, onClose, onSelect }: ClientPickerModalProps) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Client[]>([])
  const [searched, setSearched] = useState(false)
  const [loading, setLoading] = useState(false)
  const [creating, setCreating] = useState(false)
  const [error, setError] = useState<ApiError | null>(null)
  const [showQuickCreate, setShowQuickCreate] = useState(false)
  const [quickIdentificationType, setQuickIdentificationType] =
    useState<IdentificationType>('cedula')
  const [quickIdentification, setQuickIdentification] = useState('')
  const [quickPersonType, setQuickPersonType] = useState<PersonType>('natural')
  const [quickLegalName, setQuickLegalName] = useState('')
  const [quickEmail, setQuickEmail] = useState('')
  const [quickPhone, setQuickPhone] = useState('')
  const [quickAddressLine, setQuickAddressLine] = useState('')
  const searchRequestId = useRef(0)

  useEffect(() => {
    if (!visible) return
    searchRequestId.current += 1
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setCreating(false)
    setError(null)
    setShowQuickCreate(false)
    resetQuickForm()
  }, [visible])

  function resetQuickForm() {
    setQuickIdentificationType('cedula')
    setQuickIdentification('')
    setQuickPersonType('natural')
    setQuickLegalName('')
    setQuickEmail('')
    setQuickPhone('')
    setQuickAddressLine('')
  }

  function resetState() {
    setQuery('')
    setResults([])
    setSearched(false)
    setLoading(false)
    setCreating(false)
    setError(null)
    setShowQuickCreate(false)
    resetQuickForm()
  }

  function close() {
    resetState()
    onClose()
  }

  async function search(nextQuery = query) {
    const q = nextQuery.trim()
    if (q.length < 3) return
    const requestId = searchRequestId.current + 1
    searchRequestId.current = requestId
    setLoading(true)
    setError(null)
    try {
      const page = await clientsApi.list({ q })
      if (requestId !== searchRequestId.current) return
      setResults(page.items)
      setSearched(true)
    } catch (e) {
      if (requestId !== searchRequestId.current) return
      setError(toApiError(e))
    } finally {
      if (requestId === searchRequestId.current) {
        setLoading(false)
      }
    }
  }

  async function createQuick() {
    const identification = quickIdentification.trim()
    const legalName = quickLegalName.trim()
    const email = quickEmail.trim()
    if (!identification || !legalName || !email) return
    setCreating(true)
    setError(null)
    try {
      const phone = quickPhone.trim()
      const addressLine = quickAddressLine.trim()
      const client = await clientsApi.create(
        {
          identification,
          identification_type: quickIdentificationType,
          person_type: quickPersonType,
          legal_name: legalName,
          trade_name: '',
          special_taxpayer: false,
          emails: [email],
          phones: phone ? [phone] : [],
          addresses: addressLine ? [{ label: 'Principal', line: addressLine, city: '' }] : [],
        },
        createIdempotencyKey('client_quick_create'),
      )
      resetQuickForm()
      onSelect(client)
    } catch (e) {
      setError(toApiError(e))
    } finally {
      setCreating(false)
    }
  }

  return (
    <PickerModal
      visible={visible}
      onClose={close}
      title="Buscar cliente"
      searchPlaceholder="Razón social, nombre comercial o identificación"
      searchValue={query}
      onSearchChangeText={setQuery}
      onSearchChange={(nextQuery) => {
        if (!nextQuery) {
          setResults([])
          setSearched(false)
          return
        }
        void search(nextQuery)
      }}
      onSearchSubmit={() => search()}
      searchLoading={loading}
      headerActions={
        <Button
          variant="primary"
          size="md"
          onPress={() => {
            setError(null)
            setShowQuickCreate((current) => !current)
          }}
        >
          {showQuickCreate ? 'Ocultar' : 'Añadir'}
        </Button>
      }
      error={error}
      results={results}
      keyExtractor={(client) => client.id}
      maxDialogWidth={640}
      emptyState={<EmptyResults searched={searched} />}
      renderItem={(client) => (
        <PickerResultRow onPress={() => onSelect(client)}>
          <ClientResult client={client} />
        </PickerResultRow>
      )}
      footer={
        showQuickCreate ? (
          <QuickCreateClientForm
            identificationType={quickIdentificationType}
            onIdentificationTypeChange={setQuickIdentificationType}
            identification={quickIdentification}
            onIdentificationChange={setQuickIdentification}
            personType={quickPersonType}
            onPersonTypeChange={setQuickPersonType}
            legalName={quickLegalName}
            onLegalNameChange={setQuickLegalName}
            email={quickEmail}
            onEmailChange={setQuickEmail}
            phone={quickPhone}
            onPhoneChange={setQuickPhone}
            addressLine={quickAddressLine}
            onAddressLineChange={setQuickAddressLine}
            creating={creating}
            onSubmit={createQuick}
          />
        ) : null
      }
    />
  )
}

function EmptyResults({ searched }: { searched: boolean }) {
  const { semantic } = useTheme()
  return (
    <Text style={[styles.empty, { color: semantic.text.secondary }]}>
      {searched
        ? 'Sin resultados. También puedes añadir un cliente nuevo.'
        : 'Escribe para buscar. Si todavía no existe, usa Añadir.'}
    </Text>
  )
}

function ClientResult({ client }: { client: Client }) {
  const { semantic } = useTheme()
  return (
    <>
      <Text style={[styles.resultName, { color: semantic.text.primary }]} numberOfLines={1}>
        {client.trade_name || client.legal_name}
      </Text>
      <Text style={[styles.resultMeta, { color: semantic.text.secondary }]} numberOfLines={1}>
        {client.identification}
      </Text>
    </>
  )
}

function QuickCreateClientForm({
  identificationType,
  onIdentificationTypeChange,
  identification,
  onIdentificationChange,
  personType,
  onPersonTypeChange,
  legalName,
  onLegalNameChange,
  email,
  onEmailChange,
  phone,
  onPhoneChange,
  addressLine,
  onAddressLineChange,
  creating,
  onSubmit,
}: {
  identificationType: IdentificationType
  onIdentificationTypeChange: (value: IdentificationType) => void
  identification: string
  onIdentificationChange: (value: string) => void
  personType: PersonType
  onPersonTypeChange: (value: PersonType) => void
  legalName: string
  onLegalNameChange: (value: string) => void
  email: string
  onEmailChange: (value: string) => void
  phone: string
  onPhoneChange: (value: string) => void
  addressLine: string
  onAddressLineChange: (value: string) => void
  creating: boolean
  onSubmit: () => void
}) {
  const { semantic } = useTheme()
  return (
    <View style={[styles.quickBox, { borderColor: semantic.border.default }]}>
      <Text style={[styles.quickTitle, { color: semantic.text.primary }]}>Creación rápida</Text>

      <View style={styles.quickGrid}>
        <View style={styles.quickHalf}>
          <Text style={[styles.quickLabel, { color: semantic.text.secondary }]}>
            Tipo de identificación
          </Text>
          <SegmentedControl
            stretch
            columns={2}
            value={identificationType}
            options={CLIENT_IDENTIFICATION_OPTIONS}
            onChange={onIdentificationTypeChange}
          />
        </View>
        <View style={styles.quickHalf}>
          <Text style={[styles.quickLabel, { color: semantic.text.secondary }]}>
            Tipo de persona
          </Text>
          <SegmentedControl
            stretch
            value={personType}
            options={CLIENT_PERSON_OPTIONS}
            onChange={onPersonTypeChange}
          />
        </View>
      </View>

      <View style={styles.quickGrid}>
        <View style={styles.quickCol}>
          <FormField
            label="Identificación"
            placeholder="0102030405"
            leftIcon="finger-print-outline"
            value={identification}
            onChangeText={onIdentificationChange}
            required
          />
        </View>
        <View style={styles.quickWide}>
          <FormField
            label="Razón social / Nombres"
            placeholder="Juan Pérez"
            leftIcon="person-outline"
            value={legalName}
            onChangeText={onLegalNameChange}
            required
          />
        </View>
      </View>

      <View style={styles.quickGrid}>
        <View style={styles.quickHalf}>
          <EmailField
            label="Correo"
            placeholder="cliente@email.com"
            value={email}
            onChangeText={onEmailChange}
            required
          />
        </View>
        <View style={styles.quickHalf}>
          <PhoneField
            label="Teléfono (opcional)"
            placeholder="0999999999"
            value={phone}
            onChangeText={onPhoneChange}
          />
        </View>
      </View>

      <FormField
        label="Dirección (opcional)"
        placeholder="Dirección fiscal"
        leftIcon="location-outline"
        value={addressLine}
        onChangeText={onAddressLineChange}
      />

      <Button
        variant="secondary"
        size="md"
        isLoading={creating}
        isDisabled={!identification.trim() || !legalName.trim() || !email.trim()}
        onPress={onSubmit}
      >
        Crear y usar
      </Button>
    </View>
  )
}

const styles = StyleSheet.create({
  empty: { fontSize: typography.size.sm, padding: spacing[4], textAlign: 'center' },
  resultName: { fontSize: typography.size.base, fontWeight: typography.weight.semibold },
  resultMeta: { fontFamily: typography.fontFamily.mono, fontSize: typography.size.xs },
  quickBox: { borderRadius: radius.md, borderWidth: 1, gap: spacing[3], padding: spacing[3] },
  quickTitle: { fontSize: typography.size.sm, fontWeight: typography.weight.bold },
  quickGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: spacing[3] },
  quickCol: { flex: 1, minWidth: 140 },
  quickWide: { flex: 2, minWidth: 220 },
  quickHalf: { flex: 1, gap: spacing[2], minWidth: 220 },
  quickLabel: {
    fontSize: typography.size.xs,
    fontWeight: typography.weight.semibold,
    textTransform: 'uppercase',
  },
})
