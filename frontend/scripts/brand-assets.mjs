import { spawnSync } from 'node:child_process'
import { existsSync, mkdtempSync, readFileSync, rmSync, writeFileSync, copyFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { inflateSync } from 'node:zlib'

const command = process.argv[2]
const root = process.cwd()

const paths = {
  appJson: join(root, 'app.json'),
  lightSvg: join(root, 'public/favicon-light.svg'),
  darkSvg: join(root, 'public/favicon-dark.svg'),
  publicPng: join(root, 'public/favicon.png'),
  assetPng: join(root, 'assets/favicon.png'),
  appIcon: join(root, 'assets/icon.png'),
}

const logo = {
  cPath: 'M 300 116 A 130 130 0 1 0 300 284 L 259 250 A 77 77 0 1 1 259 150 Z',
  particles: [
    { cx: 319, cy: 100, r: 10, opacity: 1 },
    { cx: 346, cy: 147, r: 6.5, opacity: 0.75 },
    { cx: 355, cy: 200, r: 4, opacity: 0.45 },
    { cx: 346, cy: 253, r: 6.5, opacity: 0.75 },
    { cx: 319, cy: 300, r: 10, opacity: 1 },
  ],
}

const themes = {
  light: {
    gradientFrom: '#6366F1',
    gradientTo: '#3730A3',
    mark: '#FFFFFF',
    particle: '#FFFFFF',
  },
  dark: {
    gradientFrom: '#1E1B3A',
    gradientTo: '#0D0B1E',
    glow: '#6366F1',
    mark: '#6366F1',
    particle: '#818CF8',
  },
}

function renderSvg(themeName) {
  const theme = themes[themeName]
  const glow =
    themeName === 'dark'
      ? `\n    <radialGradient id="logo-glow" cx="50%" cy="50%" r="50%">\n      <stop offset="0%" stop-color="${theme.glow}" stop-opacity="0.15" />\n      <stop offset="100%" stop-color="${theme.glow}" stop-opacity="0" />\n    </radialGradient>`
      : ''
  const glowShape =
    themeName === 'dark'
      ? '\n  <ellipse cx="190" cy="200" rx="160" ry="160" fill="url(#logo-glow)" />'
      : ''
  const particles = logo.particles
    .map((particle) => {
      const opacity =
        particle.opacity === 1
          ? ''
          : ` opacity="${themeName === 'dark' ? darkOpacity(particle.opacity) : particle.opacity}"`
      return `  <circle cx="${particle.cx}" cy="${particle.cy}" r="${particle.r}" fill="${theme.particle}"${opacity} />`
    })
    .join('\n')

  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 400">
  <defs>
    <radialGradient id="logo-gradient" cx="38%" cy="30%" r="70%">
      <stop offset="0%" stop-color="${theme.gradientFrom}" />
      <stop offset="100%" stop-color="${theme.gradientTo}" />
    </radialGradient>${glow}
  </defs>
  <rect width="400" height="400" rx="72" fill="url(#logo-gradient)" />${glowShape}
  <path d="${logo.cPath}" fill="${theme.mark}" />
${particles}
</svg>
`
}

function darkOpacity(lightOpacity) {
  if (lightOpacity === 0.75) return 0.8
  if (lightOpacity === 0.45) return 0.5
  return lightOpacity
}

function renderPng(svgPath, size, targetPath) {
  const outputDir = mkdtempSync(join(tmpdir(), 'codelabs-brand-'))
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

function generate() {
  writeFileSync(paths.lightSvg, renderSvg('light'))
  writeFileSync(paths.darkSvg, renderSvg('dark'))
  renderPng(paths.lightSvg, 1024, paths.appIcon)
  renderPng(paths.lightSvg, 256, paths.assetPng)
  copyFileSync(paths.assetPng, paths.publicPng)
}

function verify() {
  assertEqualFile(paths.lightSvg, renderSvg('light'))
  assertEqualFile(paths.darkSvg, renderSvg('dark'))
  assertPng(paths.appIcon, 1024, 'assets/icon.png')
  assertPng(paths.assetPng, 256, 'assets/favicon.png')
  assertPng(paths.publicPng, 256, 'public/favicon.png')
  assertExpoDoesNotInjectCompetingFavicon()
}

function assertEqualFile(path, expected) {
  const actual = readFileSync(path, 'utf8')
  if (actual !== expected) throw new Error(`${path} is not generated from scripts/brand-assets.mjs`)
}

function assertPng(path, expectedSize, label) {
  const png = readPng(path)
  if (png.width !== expectedSize || png.height !== expectedSize) {
    throw new Error(
      `${label} must be ${expectedSize}x${expectedSize}, got ${png.width}x${png.height}`,
    )
  }

  const center = png.pixelAt(Math.floor(png.width / 2), Math.floor(png.height / 2))
  const isBrandPurple =
    center.r > 45 && center.r < 120 && center.g > 35 && center.g < 120 && center.b > 130
  if (!isBrandPurple) {
    throw new Error(`${label} center pixel does not match the CodeLabs purple brand icon`)
  }
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
