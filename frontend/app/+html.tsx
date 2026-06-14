import React from 'react'
import { ScrollViewStyleReset, useServerDocumentContext } from 'expo-router/html'
import { faviconAssets } from '@/constants/branding'
import { darkSemantic, lightSemantic } from '@/constants/tokens'

export default function Root({ children }: { children: React.ReactNode }) {
  const { htmlAttributes, bodyAttributes, headNodes, bodyNodes } = useServerDocumentContext()

  return (
    <html lang="en" {...htmlAttributes}>
      <head>
        <meta charSet="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no" />
        <meta httpEquiv="X-UA-Compatible" content="IE=edge" />
        <ScrollViewStyleReset />
        {headNodes}
        <link rel="icon" type="image/png" sizes="256x256" href={faviconAssets.png} />
        <link
          rel="icon"
          type="image/svg+xml"
          href={faviconAssets.light}
          media="(prefers-color-scheme: light)"
        />
        <link
          rel="icon"
          type="image/svg+xml"
          href={faviconAssets.dark}
          media="(prefers-color-scheme: dark)"
        />
        <meta
          name="theme-color"
          content={lightSemantic.bg.primary}
          media="(prefers-color-scheme: light)"
        />
        <meta
          name="theme-color"
          content={darkSemantic.bg.primary}
          media="(prefers-color-scheme: dark)"
        />
      </head>
      <body {...bodyAttributes}>
        {children}
        {bodyNodes}
      </body>
    </html>
  )
}
