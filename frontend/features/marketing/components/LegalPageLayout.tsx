import React from 'react'
import { ScrollView, StyleSheet, Text, View } from 'react-native'
import { useTheme } from '@/lib/theme-context'
import { colors, overlay, radius, spacing, typography } from '@/constants/tokens'
import type { LegalContent } from '../content/legal'
import { LandingFooter } from './LandingFooter'
import { LandingHeader } from './LandingHeader'

interface LegalPageLayoutProps {
  content: LegalContent
}

export function LegalPageLayout({ content }: LegalPageLayoutProps) {
  const { semantic } = useTheme()

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView showsVerticalScrollIndicator={false}>
        <LandingHeader />

        <View style={styles.hero}>
          <Text style={styles.heroTitle}>{content.title}</Text>
          <Text style={styles.heroSubtitle}>Última actualización: {content.lastUpdated}</Text>
        </View>

        <View style={styles.body}>
          <Text style={[styles.intro, { color: semantic.text.secondary }]}>{content.intro}</Text>

          {content.sections.map((section) => (
            <View key={section.heading} style={styles.section}>
              <Text style={[styles.sectionTitle, { color: semantic.text.primary }]}>
                {section.heading}
              </Text>
              {section.blocks.map((block, index) =>
                block.type === 'p' ? (
                  <Text key={index} style={[styles.paragraph, { color: semantic.text.secondary }]}>
                    {block.text}
                  </Text>
                ) : (
                  <View key={index} style={styles.list}>
                    {block.items.map((item) => (
                      <View key={item} style={styles.listItem}>
                        <View
                          style={[styles.bullet, { backgroundColor: semantic.accent.default }]}
                        />
                        <Text style={[styles.listText, { color: semantic.text.secondary }]}>
                          {item}
                        </Text>
                      </View>
                    ))}
                  </View>
                ),
              )}
            </View>
          ))}
        </View>

        <LandingFooter />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  hero: {
    backgroundColor: colors.nav,
    paddingHorizontal: spacing[5],
    paddingTop: spacing[4],
    paddingBottom: spacing[8],
    gap: spacing[2],
  },
  heroTitle: {
    color: overlay.text.primary,
    fontSize: typography.size['3xl'],
    fontWeight: typography.weight.bold,
    letterSpacing: -0.5,
    lineHeight: typography.size['3xl'] * typography.lineHeight.tight,
  },
  heroSubtitle: {
    color: overlay.text.subtle,
    fontSize: typography.size.sm,
    fontWeight: typography.weight.medium,
  },
  body: {
    alignSelf: 'center',
    gap: spacing[8],
    maxWidth: 720,
    paddingHorizontal: spacing[5],
    paddingVertical: spacing[8],
    width: '100%',
  },
  intro: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  },
  section: { gap: spacing[3] },
  sectionTitle: {
    fontSize: typography.size.xl,
    fontWeight: typography.weight.bold,
    lineHeight: typography.size.xl * typography.lineHeight.tight,
  },
  paragraph: {
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  },
  list: { gap: spacing[2] },
  listItem: { flexDirection: 'row', gap: spacing[3] },
  bullet: { borderRadius: radius.full, height: 6, marginTop: spacing[3], width: 6 },
  listText: {
    flex: 1,
    fontSize: typography.size.base,
    lineHeight: typography.size.base * typography.lineHeight.relaxed,
  },
})
