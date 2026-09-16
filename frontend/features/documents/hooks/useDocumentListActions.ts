import { Linking } from 'react-native'
import { useFormSubmit } from '@/lib/hooks/useFormSubmit'
import { documentsApi } from '../api'
import { useRetryDocument } from './useRetryDocument'

export function useDocumentListActions(onRefresh: () => void) {
  const { error: downloadError, submit: downloadRide } = useFormSubmit(
    async (documentId: string) => {
      const { url } = await documentsApi.getRideUrl(documentId)
      await Linking.openURL(url)
    },
  )
  const { error: downloadXmlError, submit: downloadXml } = useFormSubmit(
    async (documentId: string) => {
      const { url } = await documentsApi.getXmlUrl(documentId)
      await Linking.openURL(url)
    },
  )
  const { error: retryError, submit: retryDocument } = useRetryDocument(onRefresh)

  return { downloadError, downloadRide, downloadXmlError, downloadXml, retryError, retryDocument }
}
