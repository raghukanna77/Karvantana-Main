/** Page voice-guide — speaks a short welcome/instruction line per page in the
 *  user's selected language, using the existing per-language TTS fallback.
 *
 *  - Fires once per page per browser session (sessionStorage guard), so it
 *    greets on arrival but never nags on every revisit.
 *  - Honors the voiceGuidance setting (default ON; user can mute in Profile
 *    and on the welcome screen).
 *  - Waits for the first user interaction (pointer/key) before speaking,
 *    because browsers block speech synthesis until the page has interaction.
 *  - Cancelled on route change; never throws.
 */

import { useEffect, useRef } from 'react'
import { useLocation } from 'react-router-dom'
import { speak, stopSpeaking, ttsSupported } from '../voice/voice'
import { useT } from '../i18n'
import { useUi } from '../state/stores'

/** Pages that get a voice line, with their i18n keys. */
const PAGE_LINES: Array<[prefix: string, key: string]> = [
  ['/', 'vg.home'],
  ['/artisan/products/new', 'vg.add_product'],
  ['/artisan/products', 'vg.products'],
  ['/artisan/orders', 'vg.orders'],
  ['/artisan/customers', 'vg.customers'],
  ['/artisan/insights', 'vg.insights'],
  ['/artisan/profile', 'vg.profile'],
  ['/artisan', 'vg.studio'],
  ['/explore', 'vg.explore'],
  ['/product', 'vg.product'],
  ['/checkout', 'vg.checkout'],
  ['/buyer/orders', 'vg.orders'],
  ['/assistant', 'vg.assistant'],
  ['/b2b', 'vg.b2b'],
  ['/notifications', 'vg.notifications'],
  ['/login', 'vg.login'],
  ['/welcome', 'vg.welcome'],
]

const SKIP_PREFIXES = ['/admin', '/cluster', '/demo', '/artisan-u']

function lineKeyFor(pathname: string): string | null {
  if (SKIP_PREFIXES.some((p) => pathname.startsWith(p))) return null
  let best: string | null = null
  let bestLen = -1
  for (const [prefix, key] of PAGE_LINES) {
    if (pathname.startsWith(prefix) && prefix.length > bestLen) {
      best = key
      bestLen = prefix.length
    }
  }
  return best
}

const SAID_KEY = 'karvantana.voiceguide'

function alreadySaid(pathname: string): boolean {
  try {
    const said = JSON.parse(sessionStorage.getItem(SAID_KEY) ?? '[]') as string[]
    return said.includes(pathname)
  } catch {
    return false
  }
}

function markSaid(pathname: string): void {
  try {
    const said = JSON.parse(sessionStorage.getItem(SAID_KEY) ?? '[]') as string[]
    if (!said.includes(pathname)) {
      said.push(pathname)
      sessionStorage.setItem(SAID_KEY, JSON.stringify(said.slice(-20)))
    }
  } catch {
    /* private mode — will just speak every visit */
  }
}

/** Mount once near the app root. Reads the current route and narrates it. */
export function useVoiceGuide(): void {
  const location = useLocation()
  const { t, lang } = useT()
  const spokenRef = useRef('')

  useEffect(() => {
    if (!ttsSupported()) return
    if (!useUi.getState().voiceGuidance) return

    const key = lineKeyFor(location.pathname)
    if (!key) return
    const sig = `${location.pathname}|${lang}`
    if (spokenRef.current === sig) return
    spokenRef.current = sig

    stopSpeaking()
    if (alreadySaid(location.pathname)) return

    const text = t(key)
    if (!text) return

    let done = false
    const speakNow = () => {
      if (done) return
      done = true
      if (!useUi.getState().voiceGuidance) return
      speak(text, lang)
      markSaid(location.pathname)
    }

    // If the user has already interacted with the page, speak immediately;
    // otherwise wait for the first interaction (browser autoplay policy).
    let interacted = false
    const mark = () => { interacted = true }
    window.addEventListener('pointerdown', mark, { once: true, capture: true })
    window.addEventListener('keydown', mark, { once: true, capture: true })

    // Heuristic: after mount, try once; if speech gets blocked it fails
    // silently and the interaction listener covers the next tap.
    const timer = window.setTimeout(speakNow, 350)
    const onFirstTouch = () => { if (!interacted) return; speakNow() }
    window.addEventListener('pointerdown', onFirstTouch, { once: true })
    window.addEventListener('keydown', onFirstTouch, { once: true })

    return () => {
      window.clearTimeout(timer)
      window.removeEventListener('pointerdown', onFirstTouch)
      window.removeEventListener('keydown', onFirstTouch)
      done = true
    }
  }, [location.pathname, lang, t])
}

/** Small floating control to mute/replay the voice guide. */
export function VoiceGuideButton() {
  const location = useLocation()
  const on = useUi((s) => s.voiceGuidance)
  const setOn = useUi((s) => s.setVoiceGuidance)
  const { t, lang } = useT()

  if (!ttsSupported()) return null

  function replay() {
    const key = lineKeyFor(location.pathname)
    if (key) speak(t(key), lang)
  }

  return (
    <button
      className="k-voice-guide-btn"
      title={on ? t('vg.mute') : t('vg.unmute')}
      aria-label={on ? t('vg.mute') : t('vg.unmute')}
      onClick={() => {
        if (on) stopSpeaking()
        else replay()
        setOn(!on)
      }}
      onDoubleClick={replay}
    >
      {on ? '🔊' : '🔇'}
    </button>
  )
}
