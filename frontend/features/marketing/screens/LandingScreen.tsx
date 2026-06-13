import React, { useRef, useState } from 'react'
import { ScrollView, StyleSheet, View } from 'react-native'
import { useRouter } from 'expo-router'
import { useTheme } from '@/lib/theme-context'
import { Routes } from '@/constants/routes'
import { FeaturesSection } from '../components/FeaturesSection'
import { FinalCtaSection } from '../components/FinalCtaSection'
import { HeroSection } from '../components/HeroSection'
import { HowItWorksSection } from '../components/HowItWorksSection'
import { LandingFooter } from '../components/LandingFooter'
import { LandingHeader } from '../components/LandingHeader'
import { PlansSection } from '../components/PlansSection'

export function LandingScreen() {
  const { semantic } = useTheme()
  const router = useRouter()
  const scrollRef = useRef<ScrollView>(null)
  const [plansOffset, setPlansOffset] = useState(0)

  const scrollToPlans = () => {
    scrollRef.current?.scrollTo({ y: plansOffset, animated: true })
  }

  return (
    <View style={[styles.container, { backgroundColor: semantic.bg.page }]}>
      <ScrollView ref={scrollRef} showsVerticalScrollIndicator={false}>
        <LandingHeader />
        <HeroSection
          onCreateAccount={scrollToPlans}
          onLogin={() => router.push(Routes.auth.login)}
        />
        <FeaturesSection />
        <HowItWorksSection />
        <PlansSection onLayout={(event) => setPlansOffset(event.nativeEvent.layout.y)} />
        <FinalCtaSection onCreateAccount={scrollToPlans} />
        <LandingFooter />
      </ScrollView>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
})
