import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync, copyFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { inflateSync } from 'node:zlib'

// public/wordmark-dark.png (logo usado en los emails transaccionales, ver
// brevo_email_sender.py) no se genera aqui: qlmanage renderiza mal SVG no
// cuadrados (recorta el contenido). Si el wordmark cambia, regenerarlo con un
// navegador headless (Playwright/Chromium) a partir de
// assets/brand/wali/wordmark-dark-transparent.svg, no con qlmanage.

const command = process.argv[2]
const root = process.cwd()
const brandDir = join(root, 'assets/brand/wali')

const paths = {
  appJson: join(root, 'app.json'),
  sourceLight: join(brandDir, 'icon-app-light.svg'),
  sourceDark: join(brandDir, 'icon-app-dark.svg'),
  sourceForeground: join(brandDir, 'icon-w-on-light-transparent.svg'),
  lightSvg: join(root, 'public/favicon-light.svg'),
  darkSvg: join(root, 'public/favicon-dark.svg'),
  publicPng: join(root, 'public/favicon.png'),
  assetPng: join(root, 'assets/favicon.png'),
  appIcon: join(root, 'assets/icon.png'),
  androidForeground: join(root, 'assets/android-icon-foreground.png'),
  androidBackground: join(root, 'assets/android-icon-background.png'),
  androidMonochrome: join(root, 'assets/android-icon-monochrome.png'),
}

const brandBackgroundLight = '#F7F8FC'

const androidBackgroundSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <rect width="512" height="512" fill="${brandBackgroundLight}" />
</svg>
`

const monochromeWSvg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
<g transform="translate(117.8,355.9) scale(0.3647,-0.3647)" fill="none" stroke="#000000" stroke-width="158.0" stroke-linecap="round" stroke-linejoin="round">
<path d="M79.0,469.0 L229.0,79.0 L379.0,469.0" /><path d="M379.0,469.0 L529.0,79.0 L679.0,469.0" /></g>
</svg>
`

// Pixel de control para el fondo: lejos del W y de las esquinas redondeadas
// del icono, en cualquier tamano de render (fraccion del lado del canvas).
const backgroundProbe = { xFrac: 0.5, yFrac: 40 / 512 }

function renderPng(svgPath, size, targetPath) {
  const outputDir = mkdtempSync(join(tmpdir(), 'wali-brand-'))
  const result = spawnSync('qlmanage', ['-t', '-s', String(size), '-o', outputDir, svgPath], {
    encoding: 'utf8',
  })

  if (result.status !== 0) {
    throw new Error(
      `qlmanage failed while rendering ${svgPath}:\n${result.stderr || result.stdout}`,
    )
  }

  const renderedPath = join(outputDir, `${svgPath.split('/').at(-1)}.png`)
  if (!existsSync(renderedPath)) {
    throw new Error(`Expected qlmanage output was not created: ${renderedPath}`)
  }

  copyFileSync(renderedPath, targetPath)
  rmSync(outputDir, { recursive: true, force: true })
}

function renderInlineSvgToPng(svgContent, size, targetPath) {
  const tmpDir = mkdtempSync(join(tmpdir(), 'wali-brand-src-'))
  const tmpSvg = join(tmpDir, 'source.svg')
  writeFileSync(tmpSvg, svgContent)
  renderPng(tmpSvg, size, targetPath)
  rmSync(tmpDir, { recursive: true, force: true })
}

function generate() {
  copyFileSync(paths.sourceLight, paths.lightSvg)
  copyFileSync(paths.sourceDark, paths.darkSvg)
  renderPng(paths.lightSvg, 1024, paths.appIcon)
  renderPng(paths.lightSvg, 256, paths.assetPng)
  copyFileSync(paths.assetPng, paths.publicPng)

  renderPng(paths.sourceForeground, 512, paths.androidForeground)
  renderInlineSvgToPng(androidBackgroundSvg, 512, paths.androidBackground)
  renderInlineSvgToPng(monochromeWSvg, 432, paths.androidMonochrome)
}

function verify() {
  assertEqualFile(paths.lightSvg, paths.sourceLight)
  assertEqualFile(paths.darkSvg, paths.sourceDark)
  assertPng(paths.appIcon, 1024, 'assets/icon.png')
  assertPng(paths.assetPng, 256, 'assets/favicon.png')
  assertPng(paths.publicPng, 256, 'public/favicon.png')
  assertExpoDoesNotInjectCompetingFavicon()
}

function assertEqualFile(path, sourcePath) {
  const actual = readFileSync(path, 'utf8')
  const expected = readFileSync(sourcePath, 'utf8')
  if (actual !== expected) {
    throw new Error(`${path} is not copied from ${sourcePath} — run brand:generate`)
  }
}

function assertPng(path, expectedSize, label) {
  const png = readPng(path)
  if (png.width !== expectedSize || png.height !== expectedSize) {
    throw new Error(
      `${label} must be ${expectedSize}x${expectedSize}, got ${png.width}x${png.height}`,
    )
  }

  const probeX = Math.round(png.width * backgroundProbe.xFrac)
  const probeY = Math.round(png.height * backgroundProbe.yFrac)
  const probe = png.pixelAt(probeX, probeY)
  if (!isBrandBackground(probe)) {
    throw new Error(`${label} background pixel does not match the Wali brand background`)
  }
}

function isBrandBackground({ r, g, b }) {
  return r > 235 && g > 235 && b > 240
}

function assertExpoDoesNotInjectCompetingFavicon() {
  const appConfig = JSON.parse(readFileSync(paths.appJson, 'utf8'))
  if (appConfig.expo?.web?.favicon) {
    throw new Error(
      'app.json expo.web.favicon must stay unset; favicons are declared in app/+html.tsx',
    )
  }
}

function readPng(path) {
  const buffer = readFileSync(path)
  assertPngSignature(buffer, path)

  let offset = 8
  let width = 0
  let height = 0
  let colorType = 0
  const idat = []

  while (offset < buffer.length) {
    const length = buffer.readUInt32BE(offset)
    const type = buffer.toString('ascii', offset + 4, offset + 8)
    const dataStart = offset + 8
    const dataEnd = dataStart + length
    const data = buffer.subarray(dataStart, dataEnd)

    if (type === 'IHDR') {
      width = data.readUInt32BE(0)
      height = data.readUInt32BE(4)
      const bitDepth = data.readUInt8(8)
      colorType = data.readUInt8(9)
      if (bitDepth !== 8 || ![2, 6].includes(colorType)) {
        throw new Error(`${path} must be an 8-bit RGB/RGBA PNG`)
      }
    }
    if (type === 'IDAT') idat.push(data)
    if (type === 'IEND') break
    offset = dataEnd + 4
  }

  const channels = colorType === 6 ? 4 : 3
  const raw = inflateSync(Buffer.concat(idat))
  const stride = width * channels
  const pixels = Buffer.alloc(height * stride)
  let rawOffset = 0

  for (let y = 0; y < height; y += 1) {
    const filter = raw[rawOffset]
    rawOffset += 1
    const current = raw.subarray(rawOffset, rawOffset + stride)
    const previous = y === 0 ? Buffer.alloc(stride) : pixels.subarray((y - 1) * stride, y * stride)
    const target = pixels.subarray(y * stride, (y + 1) * stride)
    unfilterScanline(filter, current, previous, target, channels)
    rawOffset += stride
  }

  return {
    width,
    height,
    pixelAt(x, y) {
      const position = y * stride + x * channels
      return { r: pixels[position], g: pixels[position + 1], b: pixels[position + 2] }
    },
  }
}

function assertPngSignature(buffer, path) {
  const signature = '89504e470d0a1a0a'
  if (buffer.subarray(0, 8).toString('hex') !== signature) {
    throw new Error(`${path} is not a PNG file`)
  }
}

function unfilterScanline(filter, current, previous, target, channels) {
  for (let index = 0; index < current.length; index += 1) {
    const left = index >= channels ? target[index - channels] : 0
    const up = previous[index] ?? 0
    const upperLeft = index >= channels ? previous[index - channels] : 0

    if (filter === 0) target[index] = current[index]
    else if (filter === 1) target[index] = (current[index] + left) & 0xff
    else if (filter === 2) target[index] = (current[index] + up) & 0xff
    else if (filter === 3) target[index] = (current[index] + Math.floor((left + up) / 2)) & 0xff
    else if (filter === 4) target[index] = (current[index] + paeth(left, up, upperLeft)) & 0xff
    else throw new Error(`Unsupported PNG filter: ${filter}`)
  }
}

function paeth(left, up, upperLeft) {
  const prediction = left + up - upperLeft
  const leftDistance = Math.abs(prediction - left)
  const upDistance = Math.abs(prediction - up)
  const upperLeftDistance = Math.abs(prediction - upperLeft)
  if (leftDistance <= upDistance && leftDistance <= upperLeftDistance) return left
  if (upDistance <= upperLeftDistance) return up
  return upperLeft
}

if (command === 'generate') generate()
else if (command === 'verify') verify()
else {
  throw new Error('Usage: node scripts/brand-assets.mjs <generate|verify>')
}
