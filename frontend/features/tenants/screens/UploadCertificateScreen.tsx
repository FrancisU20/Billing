import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import type { Href } from 'expo-router'
import { useRouter } from 'expo-router'
import { Routes } from '@/constants/routes'
import { spacing, typography } from '@/constants/tokens'
import { useTheme } from '@/lib/theme-context'
import { selectUser, useAuthStore } from '@/features/auth/store'
import { CertificateSection } from '../components/CertificateSection'

export function UploadCertificateScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const user = useAuthStore(selectUser)
  const tenantId = user?.tenantId ?? null

  if (!tenantId) return null

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <View style={styles.header}>
        <Text style={[styles.title, { color: semantic.text.primary }]}>Certificado digital</Text>
        <Text style={[styles.subtitle, { color: semantic.text.secondary }]}>
          Para emitir documentos necesitamos tu certificado de firma electrónica p12.
        </Text>
      </View>

      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <CertificateSection
          tenantId={tenantId}
          canManage
          startEditing
          onUploaded={() => router.replace(Routes.tenant.dashboard as Href)}
        />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: { gap: spacing[2], padding: spacing[5], paddingTop: spacing[8] },
  title: {
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  subtitle: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.normal,
  },
  scroll: { padding: spacing[5], paddingBottom: spacing[12] },
})
