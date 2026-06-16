import React from 'react'
import { privacyContent } from '../content/legal'
import { LegalPageLayout } from '../components/LegalPageLayout'

export function PrivacyScreen() {
  return <LegalPageLayout content={privacyContent} />
}
