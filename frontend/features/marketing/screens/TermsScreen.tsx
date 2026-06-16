import React from 'react'
import { termsContent } from '../content/legal'
import { LegalPageLayout } from '../components/LegalPageLayout'

export function TermsScreen() {
  return <LegalPageLayout content={termsContent} />
}
