const FAVICON_VERSION = '20260620-1'

export const faviconAssets = {
  png: `/favicon.png?v=${FAVICON_VERSION}`,
  light: `/favicon-light.svg?v=${FAVICON_VERSION}`,
  dark: `/favicon-dark.svg?v=${FAVICON_VERSION}`,
} as const
