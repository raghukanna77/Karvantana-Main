/** KARVANTANA voice components — the SEE → HEAR → SPEAK → CONFIRM building blocks.
 *
 *  Every component degrades gracefully: when speech is unavailable the visual
 *  path (icons, number pad, choice grid) does the same job — voice is an
 *  accelerant, never a requirement.
 */
import { useEffect, useRef, useState } from 'react'
import { listen, speak, sttSupported, ttsSupported, parseAmount, type ListenHandle } from '../voice/voice'
import { type Lang } from '../i18n/languages'
import { useT } from '../i18n'
import { useUi } from '../state/stores'
import { KButton } from './index'

// ------------------------------------------------------------------ KMicButton

/** Large circular mic button. `size` controls diameter; label sits under the icon. */
export function KMicButton({
  label, onClick, listening, size = 88,
}: { label: string; onClick: () => void; listening?: boolean; size?: number }) {
  return (
    <button
      type="button"
      className={`k-mic-btn ${listening ? 'listening' : ''}`}
      style={{ width: size, height: size }}
      onClick={onClick}
      aria-label={label}
      aria-pressed={listening ?? false}
    >
      <span className="k-mic-icon" aria-hidden>🎤</span>
    </button>
  )
}

// ------------------------------------------------------------------ KVoiceCapture

/** One-tap voice capture with live transcript and self-correction without typing:
 *  "You said … ✓ Correct / 🔄 Speak again / ✏ Change (typed fallback)". */
export function KVoiceCapture({
  lang, onResult, autoSpeakPrompt, compact,
}: { lang: Lang; onResult: (text: string) => void; autoSpeakPrompt?: string; compact?: boolean }) {
  void compact
  const { t, lang: uiLang } = useT()
  const [listening, setListening] = useState(false)
  const [interim, setInterim] = useState('')
  const [final_, setFinal] = useState('')
  const [err, setErr] = useState('')
  const handle = useRef<ListenHandle | null>(null)

  useEffect(() => () => { handle.current?.stop() }, [])

  // Voice guidance: read the prompt aloud when supported (and requested).
  useEffect(() => {
    if (autoSpeakPrompt && ttsSupported() && useUi.getState().voiceGuidance) speak(autoSpeakPrompt, uiLang)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoSpeakPrompt])

  const start = () => {
    setErr(''); setInterim(''); setFinal('')
    const h = listen({
      lang,
      onInterim: (txt) => setInterim(txt),
      onFinal: (txt) => { setFinal(txt); setListening(false); onResult(txt) },
      onError: (e) => { setListening(false); setErr(e.code === 'not-allowed' ? t('err.mic_denied') : t('vc.unavailable')) },
      onEnd: () => setListening(false),
    })
    if (h) { handle.current = h; setListening(true) } else setErr(t('vc.unavailable'))
  }

  if (!sttSupported()) {
    return (
      <div className="k-voice-unsupported small muted">
        {t('home.mic_unsupported')}
      </div>
    )
  }

  if (final_) {
    return (
      <div className="k-voice-result" aria-live="polite">
        <div className="muted small">{t('vc.you_said')}</div>
        <div className="k-voice-transcript">“{final_}”</div>
        <div className="k-row" style={{ marginTop: 8 }}>
          <KButton size="sm" onClick={() => { onResult(final_) }}>{t('vc.correct')}</KButton>
          <KButton size="sm" variant="ghost" onClick={() => { setFinal(''); start() }}>{t('vc.again')}</KButton>
        </div>
        {listening && <div className="muted small">{t('home.listening')}</div>}
      </div>
    )
  }

  return (
    <div className="k-voice-capture">
      {!final_ && !listening && (
        <KButton variant="gold" onClick={start} aria-label={t('vc.speak_now')}>🎤 {t('vc.speak_now')}</KButton>
      )}
      {listening && (
        <div className="k-voice-live" aria-live="polite">
          <span className="k-voice-pulse" aria-hidden>🎤</span>
          <div>
            <div className="k-voice-transcript">{interim || t('home.listening')}</div>
            <button className="k-btn sm ghost" onClick={() => handle.current?.stop()}>{t('vc.tap_to_stop')}</button>
          </div>
        </div>
      )}
      {err && <div className="k-error" role="alert">{err}</div>}
    </div>
  )
}



// ------------------------------------------------------------------ KNumberPad

/** Large-touch number pad for prices/quantities + voice amount entry with confirm. */
export function KNumberPad({
  lang, title, initial, onDone, currency = '₹',
}: { lang: Lang; title: string; initial?: number; onDone: (n: number) => void; currency?: string }) {
  const { t } = useT()
  const [value, setValue] = useState(initial ? String(initial) : '')
  const [voiceHeard, setVoiceHeard] = useState<string | null>(null)
  const [confirmN, setConfirmN] = useState<number | null>(null)

  const press = (d: string) => {
    if (d === 'C') return setValue('')
    if (d === '⌫') return setValue((v) => v.slice(0, -1))
    if (d === '00' && !value) return
    if (value.length >= 9) return
    setValue(value + d)
  }

  const voiceResult = (raw: string) => {
    const n = parseAmount(raw)
    setVoiceHeard(raw)
    if (n) setConfirmN(n)
  }

  return (
    <div className="k-numpad">
      <div className="k-numpad-display" aria-live="polite">
        <span className="muted small">{title}</span>
        <div className="k-numpad-value">{currency}{value || '0'}</div>
        {voiceHeard && confirmN == null && (
          <div className="muted small">{t('np.heard_not_amount', { raw: voiceHeard })}</div>
        )}
        {confirmN != null && voiceHeard && (
          <div className="k-voice-result">
            <div className="small">{t('np.voice_parse', { raw: voiceHeard, n: confirmN })}</div>
            <div className="k-row" style={{ marginTop: 6 }}>
              <KButton size="sm" onClick={() => { setValue(String(confirmN)); setConfirmN(null); setVoiceHeard(null) }}>{t('vc.correct')}</KButton>
              <KButton size="sm" variant="ghost" onClick={() => { setConfirmN(null); setVoiceHeard(null) }}>{t('vc.again')}</KButton>
            </div>
          </div>
        )}
      </div>
      <div className="k-numpad-grid" role="group" aria-label={title}>
        {['1', '2', '3', '4', '5', '6', '7', '8', '9', '00', '0', '⌫'].map((d) => (
          <button key={d} type="button" className="k-numpad-key" onClick={() => press(d)}>{d}</button>
        ))}
      </div>
      <div className="k-row" style={{ marginTop: 10 }}>
        <KVoiceCapture lang={lang} onResult={voiceResult} compact />
        <KButton variant="gold" block disabled={!value} onClick={() => onDone(Number(value))}>{t('np.done')}</KButton>
      </div>
    </div>
  )
}

// ------------------------------------------------------------------ KChoiceGrid

/** Icon choice grid — the visual category selector. Speak-aloud optional. */
export function KChoiceGrid({
  options, onPick, spoken,
}: { options: { key: string; icon: string; label: string }[]; onPick: (key: string) => void; spoken?: boolean }) {
  const { lang } = useT()
  useEffect(() => {
    if (spoken && ttsSupported()) speak(options.map((o) => o.label).join(', '), lang)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])
  return (
    <div className="k-choice-grid">
      {options.map((o) => (
        <button key={o.key} type="button" className="k-choice" onClick={() => onPick(o.key)} aria-label={o.label}>
          <span className="k-choice-icon" aria-hidden>{o.icon}</span>
          <span className="k-choice-label">{o.label}</span>
        </button>
      ))}
    </div>
  )
}


