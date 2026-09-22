/** KARVANTANA language architecture v2 — 20 official Indian languages + 4 regional packs.
 *
 *  Honesty rules (non-negotiable):
 *  - `stt`/`tts` flags reflect what the browser Web Speech API actually supports today
 *    for Indian locales in Chrome/Android; anything else is `false` with a fallback.
 *  - Regional packs (gar, kfy, gon, bhb) have NO machine voice support claimed —
 *    they fall back to Hindi/English speech and fully visual UI. Never crash.
 *  - Catalog coverage is declared per language: FULL (en/ta/hi), CORE (7 major),
 *    MINIMAL (native name + tagline only), NONE (pure fallback to English UI).
 *  Adding a language = one entry here + (optionally) a catalog pack. Nothing else.
 */

export type Lang =
  | 'en' | 'hi' | 'bn' | 'mr' | 'te' | 'ta' | 'gu' | 'kn' | 'ml' | 'or'
  | 'pa' | 'as' | 'ur' | 'ne' | 'kok' | 'ks' | 'mai' | 'sat' | 'mni' | 'brx'
  | 'gar' | 'kfy' | 'gon' | 'bhb'

export type CatalogCoverage = 'FULL' | 'CORE' | 'MINIMAL' | 'NONE'
export type VoiceSupport = 'YES' | 'FALLBACK' | 'NO'
export type Region =
  | 'All India' | 'South India' | 'East India' | 'West India' | 'North India'
  | 'Himalayan' | 'North-East' | 'Central India'

export interface LanguageInfo {
  code: Lang
  /** Native name in its own script — shown first, this is how users find their language. */
  nativeName: string
  englishName: string
  region: Region
  /** BCP-47 locale for SpeechRecognition / speechSynthesis. */
  locale: string
  rtl?: boolean
  catalog: CatalogCoverage
  stt: VoiceSupport
  tts: VoiceSupport
  /** When speech is unavailable, listen in this language instead. */
  sttFallback?: Lang
  ttsFallback?: Lang
}

export const LANGUAGES: LanguageInfo[] = [
  // Priority order per product spec (Hindi & English first for reach).
  { code: 'hi', nativeName: 'हिन्दी', englishName: 'Hindi', region: 'All India', locale: 'hi-IN', catalog: 'FULL', stt: 'YES', tts: 'YES' },
  { code: 'en', nativeName: 'English', englishName: 'English', region: 'All India', locale: 'en-IN', catalog: 'FULL', stt: 'YES', tts: 'YES' },
  { code: 'bn', nativeName: 'বাংলা', englishName: 'Bengali', region: 'East India', locale: 'bn-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'mr', nativeName: 'मराठी', englishName: 'Marathi', region: 'West India', locale: 'mr-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'te', nativeName: 'తెలుగు', englishName: 'Telugu', region: 'South India', locale: 'te-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'ta', nativeName: 'தமிழ்', englishName: 'Tamil', region: 'South India', locale: 'ta-IN', catalog: 'FULL', stt: 'YES', tts: 'YES' },
  { code: 'gu', nativeName: 'ગુજરાતી', englishName: 'Gujarati', region: 'West India', locale: 'gu-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'kn', nativeName: 'ಕನ್ನಡ', englishName: 'Kannada', region: 'South India', locale: 'kn-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'ml', nativeName: 'മലയാളം', englishName: 'Malayalam', region: 'South India', locale: 'ml-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'or', nativeName: 'ଓଡ଼ିଆ', englishName: 'Odia', region: 'East India', locale: 'or-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'pa', nativeName: 'ਪੰਜਾਬੀ', englishName: 'Punjabi', region: 'North India', locale: 'pa-Guru-IN', catalog: 'CORE', stt: 'YES', tts: 'YES' },
  { code: 'as', nativeName: 'অসমীয়া', englishName: 'Assamese', region: 'North-East', locale: 'as-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'bn', ttsFallback: 'bn' },
  { code: 'ur', nativeName: 'اردو', englishName: 'Urdu', region: 'North India', locale: 'ur-IN', rtl: true, catalog: 'NONE', stt: 'YES', tts: 'YES' },
  { code: 'ne', nativeName: 'नेपाली', englishName: 'Nepali', region: 'Himalayan', locale: 'ne-NP', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'kok', nativeName: 'कोंकणी', englishName: 'Konkani', region: 'West India', locale: 'kok-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'mr', ttsFallback: 'mr' },
  { code: 'ks', nativeName: 'کٲشُر', englishName: 'Kashmiri', region: 'Himalayan', locale: 'ks-IN', rtl: true, catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'ur', ttsFallback: 'hi' },
  { code: 'mai', nativeName: 'मैथिली', englishName: 'Maithili', region: 'East India', locale: 'mai-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'sat', nativeName: 'ᱥᱟᱱᱛᱟᱲᱤ', englishName: 'Santali', region: 'East India', locale: 'sat-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'mni', nativeName: 'ꯃꯤꯇꯩꯂꯣꯟ', englishName: 'Manipuri (Meitei)', region: 'North-East', locale: 'mni-Mtei-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'bn', ttsFallback: 'bn' },
  { code: 'brx', nativeName: 'बड़ो', englishName: 'Bodo', region: 'North-East', locale: 'brx-IN', catalog: 'NONE', stt: 'NO', tts: 'NO', sttFallback: 'as', ttsFallback: 'bn' },
  // Regional language packs — visual-first, speech falls back. Never claim voice we don't have.
  { code: 'gar', nativeName: 'गढ़वळि', englishName: 'Garhwali', region: 'Himalayan', locale: 'gar-IN', catalog: 'MINIMAL', stt: 'FALLBACK', tts: 'FALLBACK', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'kfy', nativeName: 'कुमाऊँनी', englishName: 'Kumaoni', region: 'Himalayan', locale: 'kfy-IN', catalog: 'MINIMAL', stt: 'FALLBACK', tts: 'FALLBACK', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'gon', nativeName: 'गोंडी', englishName: 'Gondi', region: 'Central India', locale: 'gon-IN', catalog: 'MINIMAL', stt: 'FALLBACK', tts: 'FALLBACK', sttFallback: 'hi', ttsFallback: 'hi' },
  { code: 'bhb', nativeName: 'भिली', englishName: 'Bhili', region: 'West India', locale: 'bhb-IN', catalog: 'MINIMAL', stt: 'FALLBACK', tts: 'FALLBACK', sttFallback: 'gu', ttsFallback: 'hi' },
]

export const LANG_CODES = LANGUAGES.map((l) => l.code)

const byCode = new Map(LANGUAGES.map((l) => [l.code, l]))
export function languageInfo(code: Lang): LanguageInfo {
  return byCode.get(code) ?? byCode.get('en')!
}

/** Which region packs exist for the "regional language packs" architecture. */
export const REGIONAL_PACKS = LANGUAGES.filter((l) =>
  ['gar', 'kfy', 'gon', 'bhb'].includes(l.code))

export function langDir(code: Lang): 'ltr' | 'rtl' {
  return languageInfo(code).rtl ? 'rtl' : 'ltr'
}

/** Effective speech locale with fallback — never throws, never returns an unsupported pair. */
export function speechLocale(code: Lang): { locale: string; fellBack: boolean } {
  const info = languageInfo(code)
  if (info.stt !== 'NO') return { locale: info.locale, fellBack: false }
  const fb = languageInfo(info.sttFallback ?? 'hi')
  return { locale: fb.locale, fellBack: true }
}

/** Effective TTS locale with fallback. */
export function ttsLocale(code: Lang): { locale: string; fellBack: boolean } {
  const info = languageInfo(code)
  if (info.tts !== 'NO') return { locale: info.locale, fellBack: false }
  const fb = languageInfo(info.ttsFallback ?? 'hi')
  return { locale: fb.locale, fellBack: true }
}
