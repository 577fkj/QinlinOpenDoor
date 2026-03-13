import fs from 'fs'
import path from 'path'
import { fileURLToPath } from 'url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const distTempDir = path.join(__dirname, 'dist_temp')
const templatesDir = path.join(__dirname, '..', 'templates')
const staticDir = path.join(__dirname, '..', 'static')

function cleanDirs() {
  [templatesDir, staticDir].forEach(dir => {
    if (fs.existsSync(dir)) fs.rmSync(dir, { recursive: true, force: true })
  })
}

function copyDirRecursive(src, dest) {
  fs.mkdirSync(dest, { recursive: true })
  fs.readdirSync(src, { withFileTypes: true }).forEach(entry => {
    const srcPath = path.join(src, entry.name)
    const destPath = path.join(dest, entry.name)
    entry.isDirectory() ? copyDirRecursive(srcPath, destPath) : fs.copyFileSync(srcPath, destPath)
  })
}

function moveIcons() {
  const iconsDir = path.join(staticDir, 'icons')
  fs.mkdirSync(iconsDir, { recursive: true })
  
  const isIconFile = file => file.endsWith('.png') && (file.includes('icon') || file.includes('favicon'))
  
  if (fs.existsSync(distTempDir)) {
    fs.readdirSync(distTempDir).filter(isIconFile).forEach(file => {
      fs.copyFileSync(path.join(distTempDir, file), path.join(iconsDir, file))
    })
  }
  
  fs.readdirSync(staticDir).filter(isIconFile).forEach(file => {
    fs.renameSync(path.join(staticDir, file), path.join(iconsDir, file))
  })
}

function processHTML() {
  const distIndexPath = path.join(distTempDir, 'index.html')
  if (!fs.existsSync(distIndexPath)) return { js: [], css: [] }
  
  const content = fs.readFileSync(distIndexPath, 'utf-8')
  const assets = {
    js: [...new Set(content.match(/\/static\/js\/[^"']+\.js/g) || [])],
    css: [...new Set(content.match(/\/static\/css\/[^"']+\.css/g) || [])]
  }
  
  fs.mkdirSync(templatesDir, { recursive: true })
  fs.writeFileSync(path.join(templatesDir, 'index.html'), content)
  return assets
}

function generateServiceWorker(assets) {
  const swTemplatePath = path.join(__dirname, 'public', 'sw.template.js')
  if (!fs.existsSync(swTemplatePath)) return
  
  const urlsToCache = ['/{{token}}/', '/{{token}}/manifest.json', '/static/icons/icon-192x192.png', '/static/icons/icon-512x512.png', ...assets.css, ...assets.js]
  
  let swContent = fs.readFileSync(swTemplatePath, 'utf-8')
    .replace('CACHE_VERSION_PLACEHOLDER', `door-control-v${Date.now()}`)
    .replace('URLS_TO_CACHE_PLACEHOLDER', JSON.stringify(urlsToCache, null, 4))
  
  fs.mkdirSync(path.join(staticDir, 'js'), { recursive: true })
  fs.writeFileSync(path.join(staticDir, 'js', 'sw.js'), swContent)
}

cleanDirs()
const assets = processHTML()

const distStaticPath = path.join(distTempDir, 'static')
if (fs.existsSync(distStaticPath)) copyDirRecursive(distStaticPath, staticDir)

moveIcons()
generateServiceWorker(assets)

const manifestSrc = path.join(__dirname, 'public', 'manifest.json')
if (fs.existsSync(manifestSrc)) {
  fs.copyFileSync(manifestSrc, path.join(staticDir, 'manifest.json'))
}

if (fs.existsSync(distTempDir)) fs.rmSync(distTempDir, { recursive: true, force: true })

console.log('✓ 构建完成')
