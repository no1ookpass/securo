/// <reference types="node" />
import { readFileSync, readdirSync } from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'
import i18next, { type Resource } from 'i18next'

import {
  CATEGORY_ICONS,
  getCategoryIconLabel,
  ICON_MAP,
  isEmoji,
} from '@/lib/category-icons'
import en from '@/locales/en.json'
import ptBR from '@/locales/pt-BR.json'

const LOCALES_DIR = path.resolve(
  path.dirname(fileURLToPath(import.meta.url)),
  '../locales',
)

function makeT(lng: string, resources: Resource, fallbackLng: string | false = false) {
  const instance = i18next.createInstance()
  instance.init({ lng, resources, fallbackLng, initImmediate: false })
  return instance.t
}

describe('CATEGORY_ICONS', () => {
  it('has no duplicate names', () => {
    // A duplicate would silently win in ICON_MAP and shadow the other entry.
    const names = CATEGORY_ICONS.map((entry) => entry.name)
    expect(new Set(names).size).toBe(names.length)
  })

  it('gives every entry a name, a fallback label and a component', () => {
    for (const entry of CATEGORY_ICONS) {
      expect(entry.name, 'name').toMatch(/^[a-z0-9-]+$/)
      expect(entry.pt, `${entry.name} pt`).not.toBe('')
      expect(entry.icon, `${entry.name} icon`).toBeDefined()
    }
  })
})

describe('categoryIcons locale blocks', () => {
  it('keeps every locale block in step with the catalogue', () => {
    // A key missing from one locale would fall back to the Portuguese label,
    // which is exactly what issue 880 was about. Every shipped locale must
    // therefore carry the same keys, and every key must name an icon the
    // catalogue can render.
    //
    // Fork note: this branch ships a much larger picker than upstream (the
    // curated set plus the rest of the Lucide library in CATEGORY_ICONS), so
    // "every catalogue icon in every locale" is 200x18 translations. The
    // extended icons deliberately fall back to their `pt` label; key parity
    // and the en.json block are what keep the translated ones honest.
    const files = readdirSync(LOCALES_DIR)
      .filter((file) => file.endsWith('.json'))
      .sort()
    expect(files.length, 'locale files').toBeGreaterThanOrEqual(2)
    const blocks = new Map<string, Record<string, string>>()
    for (const file of files) {
      const data = JSON.parse(readFileSync(path.join(LOCALES_DIR, file), 'utf-8'))
      const block = data.categoryIcons
      expect(block, `${file}: categoryIcons block`).toBeDefined()
      for (const [key, label] of Object.entries(block)) {
        expect(String(label).trim(), `${file}: ${key}`).not.toBe('')
      }
      blocks.set(file, block as Record<string, string>)
    }
    const english = blocks.get('en.json')
    expect(english, 'en.json: categoryIcons block').toBeDefined()
    const translated = Object.keys(english!).sort()
    for (const [file, block] of blocks) {
      expect(Object.keys(block).sort(), `${file}: icon keys`).toEqual(translated)
    }
    const orphans = translated.filter((name) => !(name in ICON_MAP))
    expect(orphans, 'translated keys with no catalogue icon').toEqual([])
  })
})

describe('getCategoryIconLabel', () => {
  it('returns the English label under the English bundle', () => {
    const t = makeT('en', { en: { translation: en } })
    expect(getCategoryIconLabel(t, 'heart')).toBe('Health / Wellbeing')
  })

  it('returns the Portuguese label under the pt-BR bundle', () => {
    const t = makeT('pt-BR', { 'pt-BR': { translation: ptBR } })
    expect(getCategoryIconLabel(t, 'heart')).toBe('Saúde / Bem-estar')
  })

  it('uses the app fallback language when the locale has no key', () => {
    // Same fallbackLng as the app (lib/i18n.ts).
    const t = makeT('de', { de: { translation: {} }, en: { translation: en } }, 'en')
    expect(getCategoryIconLabel(t, 'heart')).toBe('Health / Wellbeing')
  })

  it('falls back to the Portuguese label when no language has the key', () => {
    const t = makeT('de', { de: { translation: {} } })
    expect(getCategoryIconLabel(t, 'heart')).toBe('Saúde / Bem-estar')
  })

  it('falls back to the raw name for an icon the catalogue does not know', () => {
    const t = makeT('en', { en: { translation: en } })
    expect(getCategoryIconLabel(t, 'not-an-icon')).toBe('not-an-icon')
  })
})

describe('ICON_MAP', () => {
  it('exposes every catalogue entry for lookup', () => {
    expect(Object.keys(ICON_MAP)).toHaveLength(CATEGORY_ICONS.length)
    for (const entry of CATEGORY_ICONS) {
      expect(ICON_MAP[entry.name]).toBe(entry.icon)
    }
  })

  it('returns nothing for a name it does not know', () => {
    // CategoryIcon relies on this being undefined so it can fall back rather
    // than render a blank box.
    expect(ICON_MAP['not-a-real-icon']).toBeUndefined()
  })
})

describe('default categories', () => {
  it('only seeds icons the catalogue can render', () => {
    // The backend seeds these names into every new workspace. One missing from
    // the catalogue shows up as the "?" fallback instead of its own icon.
    const file = path.resolve(
      path.dirname(fileURLToPath(import.meta.url)),
      '../../../backend/app/data/default_categories.json',
    )
    const taxonomy = JSON.parse(readFileSync(file, 'utf-8')) as {
      groups: Record<string, { icon: string }>
      categories: Record<string, { icon: string }>
    }
    const seeded = [
      ...Object.values(taxonomy.groups),
      ...Object.values(taxonomy.categories),
    ].map((entry) => entry.icon)
    const missing = [...new Set(seeded)].filter((icon) => !(icon in ICON_MAP))
    expect(missing).toEqual([])
  })
})

describe('isEmoji', () => {
  it('recognises the emoji stored by older category rows', () => {
    expect(isEmoji('🍔')).toBe(true)
    expect(isEmoji('🏠')).toBe(true)
    expect(isEmoji('💰')).toBe(true)
  })

  it('rejects a lucide icon name', () => {
    expect(isEmoji('shopping-cart')).toBe(false)
    expect(isEmoji('house')).toBe(false)
  })

  it('rejects an empty string', () => {
    expect(isEmoji('')).toBe(false)
  })

  it('rejects a long string that merely contains an emoji', () => {
    expect(isEmoji('food 🍔')).toBe(false)
  })
})
