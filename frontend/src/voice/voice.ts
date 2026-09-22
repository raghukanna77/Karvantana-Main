/** KARVANTANA voice service — Web Speech API with honest per-language fallback.
 *
 *  Capability comes from the i18n language registry (languages.ts). When a
 *  language has no STT/TTS on this device, we fall back to the registry's
 *  fallback language and the UI says so via the `fellBack` flag. We never
 *  claim a language has voice it doesn't.
 */

import { languageInfo, type Lang } from '../i18n/languages'

export interface SpeechError {
  code: string
  message: string
}

export interface ListenOptions {
  lang: Lang
  onInterim?: (text: string) => void
  onFinal: (text: string) => void
  onError?: (err: SpeechError) => void
  onEnd?: () => void
}

export interface ListenHandle {
  stop: () => void
  locale: string
  fellBack: boolean
}

function getRecognition(): any | null {
  const w = window as any
  const Ctor = w.SpeechRecognition || w.webkitSpeechRecognition
  return Ctor ? new Ctor() : null
}

export const sttSupported = (): boolean =>
  typeof window !== 'undefined' && (!!(window as any).SpeechRecognition || !!(window as any).webkitSpeechRecognition)

/** Start listening. Returns a handle, or null when speech recognition is unavailable. Never throws. */
export function listen(opts: ListenOptions): ListenHandle | null {
  const rec = getRecognition()
  if (!rec) {
    opts.onError?.({ code: 'unsupported', message: 'Speech recognition is not available on this device' })
    return null
  }
  const info = languageInfo(opts.lang)
  const target = info.stt === 'NO' ? (info.sttFallback ?? 'hi') : opts.lang
  const fellBack = target !== opts.lang
  rec.lang = languageInfo(target).locale
  rec.continuous = false
  rec.interimResults = true
  rec.maxAlternatives = 1

  let stopped = false

  rec.onresult = (e: any) => {
    let interim = ''
    let finalText = ''
    for (let i = e.resultIndex; i < e.results.length; i++) {
      const r = e.results[i]
      if (r.isFinal) finalText += r[0].transcript
      else interim += r[0].transcript
    }
    if (interim) opts.onInterim?.(interim)
    if (finalText) opts.onFinal(finalText.trim())
  }
  rec.onerror = (e: any) => {
    stopped = true
    opts.onError?.({ code: e?.error ?? 'unknown', message: 'Speech error' })
  }
  rec.onend = () => {
    if (!stopped) opts.onEnd?.()
    stopped = true
  }
  try {
    rec.start()
  } catch {
    opts.onError?.({ code: 'start_failed', message: 'Could not start the microphone' })
    return null
  }
  return {
    stop: () => {
      stopped = true
      try { rec.stop() } catch { /* already stopped */ }
    },
    locale: rec.lang,
    fellBack,
  }
}

// ------------------------------------------------------------------ TTS

function pickVoice(locale: string): SpeechSynthesisVoice | null {
  const synth = window.speechSynthesis
  if (!synth) return null
  const voices = synth.getVoices()
  const exact = voices.find((v) => v.lang.replace('_', '-') === locale)
  const prefix = locale.split('-')[0] ?? locale
  const partial = voices.find((v) => v.lang.replace('_', '-').startsWith(prefix))
  return exact ?? partial ?? null
}

/** Speak text aloud. Returns false when TTS is unavailable (UI shows text instead). */
export function speak(text: string, lang: Lang): boolean {
  const synth = window.speechSynthesis
  if (!synth || !text) return false
  const info = languageInfo(lang)
  const target = info.tts === 'NO' ? (info.ttsFallback ?? 'hi') : lang
  const u = new SpeechSynthesisUtterance(text)
  u.lang = languageInfo(target).locale
  const v = pickVoice(u.lang)
  if (v) u.voice = v
  try {
    synth.cancel()
    synth.speak(u)
    return true
  } catch {
    return false
  }
}

export const ttsSupported = (): boolean => typeof window !== 'undefined' && !!window.speechSynthesis

export function stopSpeaking(): void {
  try { window.speechSynthesis?.cancel() } catch { /* noop */ }
}

// ------------------------------------------------------------------ amount parsing (voice price/qty)

const HI_DIGITS: Record<string, number> = {
  'शून्य': 0, 'एक': 1, 'दो': 2, 'तीन': 3, 'चार': 4, 'पाँच': 5, 'पांच': 5, 'छह': 6, 'छः': 6,
  'सात': 7, 'आठ': 8, 'नौ': 9, 'दस': 10, 'बीस': 20, 'तीस': 30, 'चालीस': 40, 'पचास': 50,
  'साठ': 60, 'सत्तर': 70, 'अस्सी': 80, 'नब्बे': 90, 'सौ': 100, 'हज़ार': 1000, 'हजार': 1000,
}

/** Parse a spoken/typed amount. Digits, Hindi words, lakh/crore. null if unparseable. */
export function parseAmount(raw: string): number | null {
  const t = raw.toLowerCase().trim()
  const digitMatch = t.replace(/,/g, '').match(/\d+(\.\d+)?/)
  if (digitMatch) {
    let n = parseFloat(digitMatch[0])
    if (n <= 0) return null
    if (/lakh|लाख/.test(t)) n *= 100000
    if (/crore|करोड़/.test(t)) n *= 10000000
    return Math.round(n)
  }
  let total = 0
  let found = false
  for (const [word, val] of Object.entries(HI_DIGITS)) {
    if (val > 0 && t.includes(word)) {
      total += val
      found = true
    }
  }
  if (!found) return null
  if (t.includes('लाख')) total *= 100000
  else if (t.includes('हज़ार') || t.includes('हजार')) total *= 1000
  else if (t.includes('सौ') && total < 10) total *= 100
  return total || null
}
