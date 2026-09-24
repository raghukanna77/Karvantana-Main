/**
 * WhatsAppSimulator — a WhatsApp-style chat front-end over the SAME listing
 * pipeline the main app drives (photo → voice → AI listing → price → publish).
 *
 * Prototype transport: this component posts each inbound exchange to
 * POST /api/v1/whatsapp/webhook and renders the OutboundMessages the state
 * machine returns (persisted server-side in whatsapp_messages). Swapping in
 * the real WhatsApp Cloud API later changes only the transport: the same
 * webhook accepts the Cloud API envelope and the same IMessagingChannel
 * delivers bot messages — this UI can then be retired or pointed at a real
 * thread with zero state-machine changes.
 *
 * Trust framing matches the main app: every generated suggestion carries the
 * gold "AI suggestion — approve or edit" tag (same treatment as ProductWizard).
 */
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'

type Kind = 'text' | 'image' | 'voice' | 'interactive' | 'pending'

interface Bubble {
  id: string
  direction: 'IN' | 'OUT'
  kind: Kind
  payload: {
    body?: string
    link?: string
    caption?: string
    duration_seconds?: number
    buttons?: { id: string; title: string }[]
    ai_tag?: boolean
  }
  created_at?: string
  /** buttons already consumed — dim them (WhatsApp keeps taps disabled after use) */
  used?: boolean
}

interface WebhookResponse {
  messages: { id: string; kind: string; payload: Record<string, unknown>; timestamp: string }[]
  state: string | null
  greeting?: { id: string; kind: string; payload: Record<string, unknown>; timestamp: string }[]
}

interface ThreadResponse {
  phone: string | null
  state: string | null
  draft_listing_id?: string | null
  published_product_id?: string | null
  messages: { id: string; direction: string; kind: string; payload: Record<string, unknown>; created_at: string }[]
}

const BOT_NAME = 'KaarigarConnect Assistant'

function clockLabel(iso?: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

/** Deterministic pseudo-waveform from the bubble id — decorative only. */
function waveform(id: string): number[] {
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  const bars: number[] = []
  for (let i = 0; i < 26; i++) {
    h = (h * 1103515245 + 12345) >>> 0
    bars.push(5 + (h % 17))
  }
  return bars
}

export default function WhatsAppSimulator() {
  const [phone, setPhone] = useState<string | null>(null)
  const [phoneDraft, setPhoneDraft] = useState('')
  const [state, setState] = useState<string | null>(null)
  const [bubbles, setBubbles] = useState<Bubble[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)          // a webhook exchange is in flight
  const [processing, setProcessing] = useState(false) // PROCESSING-state typing indicator
  const [error, setError] = useState('')
  const imageInput = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  const scrollToEnd = useCallback(() => {
    requestAnimationFrame(() => {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
    })
  }, [])

  const loadThread = useCallback(async () => {
    try {
      const t = await api.waThread<ThreadResponse>()
      setPhone(t.phone)
      setState(t.state)
      setBubbles(t.messages.map((m) => ({
        id: m.id, direction: m.direction as Bubble['direction'], kind: m.kind as Bubble['kind'],
        payload: m.payload as Bubble['payload'], created_at: m.created_at,
      })))
      scrollToEnd()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not load the chat thread.')
    }
  }, [scrollToEnd])

  useEffect(() => { void loadThread() }, [loadThread])

  const pushIn = useCallback((b: Omit<Bubble, 'direction' | 'id'>) => {
    setBubbles((prev) => [...prev, { ...b, direction: 'IN', id: `local-${Date.now()}-${Math.random()}` }])
    scrollToEnd()
  }, [scrollToEnd])

  const send = useCallback(async (fields: Record<string, string>, file?: { blob: Blob; name: string; kind: 'image' | 'audio' }) => {
    if (busy) return
    setBusy(true)
    setError('')
    setProcessing(true) // WhatsApp-style "typing…" while the pipeline runs
    try {
      const res = await api.waSend<WebhookResponse>(fields, file)
      // Greeting arrives only on first contact — insert before the reply.
      const prefix: Bubble[] = (res.greeting ?? []).map((m) => ({
        id: m.id, direction: 'OUT', kind: m.kind as Bubble['kind'],
        payload: m.payload as Bubble['payload'], created_at: m.timestamp,
      }))
      const replies: Bubble[] = res.messages.map((m) => ({
        id: m.id, direction: 'OUT', kind: m.kind as Bubble['kind'],
        payload: m.payload as Bubble['payload'], created_at: m.timestamp,
      }))
      setBubbles((prev) => [...prev, ...prefix, ...replies])
      setState(res.state)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Message failed to send.')
    } finally {
      setProcessing(false)
      setBusy(false)
      scrollToEnd()
    }
  }, [busy, scrollToEnd])

  const onPickPhoto = (f: File | null) => {
    if (!f) return
    pushIn({ kind: 'image', payload: { link: URL.createObjectURL(f), caption: f.name } })
    void send({}, { blob: f, name: f.name, kind: 'image' })
  }

  const onPickVoice = (f: File | null) => {
    if (!f) return
    // The main app captures transcripts on-device (Web Speech API); for the
    // simulator the demo STT provider maps the upload to a scripted sample,
    // exactly like the app's voice journey without mic access.
    pushIn({ kind: 'voice', payload: { duration_seconds: Math.max(1, Math.round(f.size / 8000)) } })
    void send({ language_hint: 'ta' }, { blob: f, name: f.name, kind: 'audio' })
  }

  const onText = () => {
    const t = draft.trim()
    if (!t || busy) return
    pushIn({ kind: 'text', payload: { body: t } })
    setDraft('')
    void send({ text: t })
  }

  const onButton = (b: { id: string; title: string }) => {
    setBubbles((prev) => prev.map((x) => (x.kind === 'interactive' && !x.used ? { ...x, used: true } : x)))
    pushIn({ kind: 'text', payload: { body: b.title.replace(/^[^a-zA-Z]+/, '') } })
    void send({ button_id: b.id })
  }

  const attachPhoto = () => imageInput.current?.click()

  const recordVoice = () => {
    // Prototype: a voice note is an audio attachment. Reuse the same <input
    // type=file accept=audio> pattern the main app's voice journey uses when
    // SpeechRecognition is unavailable. Deterministic demo sample chosen by
    // the backend demo STT provider.
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = 'audio/*'
    input.onchange = () => onPickVoice(input.files?.[0] ?? null)
    input.click()
  }

  const needsPhone = phone === null
  const stateChip = useMemo(() => {
    switch (state) {
      case 'AWAITING_PHOTO': return { label: 'Step 1 · send a product photo', tone: 'gold' }
      case 'AWAITING_VOICE': return { label: 'Step 2 · send a voice note', tone: 'gold' }
      case 'PROCESSING': return { label: 'AI is writing your listing…', tone: 'blue' }
      case 'REVIEW': return { label: 'Step 4 · review & publish', tone: 'green' }
      case 'EDITING': return { label: 'Editing — tell the bot what to change', tone: 'blue' }
      case 'IDLE': return { label: 'All done — ready for the next product', tone: 'green' }
      default: return null
    }
  }, [state])

  return (
    <div className="wa-stage">
      <input ref={imageInput} type="file" accept="image/*" hidden onChange={(e) => { onPickPhoto(e.target.files?.[0] ?? null); e.currentTarget.value = '' }} />
      <div className="wa-phone" role="region" aria-label={`${BOT_NAME} chat simulator`}>
        {/* header */}
        <div className="wa-header">
          <div className="wa-avatar" aria-hidden>🧵</div>
          <div className="wa-header-meta">
            <div className="wa-name">{BOT_NAME}</div>
            <div className="wa-status">{processing ? 'typing…' : 'online'} · KARVANTANA demo</div>
          </div>
          <span className={`wa-state-chip ${stateChip?.tone ?? ''}`}>{stateChip?.label ?? 'WhatsApp listing demo'}</span>
        </div>

        {/* thread */}
        <div className="wa-thread" ref={scrollRef} aria-live="polite">
          <div className="wa-day">TODAY</div>
          {needsPhone && (
            <div className="wa-setup">
              <p>Link your WhatsApp number to start. In production this is your WhatsApp account; in the demo it identifies your chat thread.</p>
              <div className="wa-setup-row">
                <input value={phoneDraft} onChange={(e) => setPhoneDraft(e.target.value)}
                       placeholder="10-digit mobile number" inputMode="numeric" aria-label="WhatsApp number" />
                <button className="wa-pill primary" disabled={busy || phoneDraft.replace(/\D/g, '').length < 10}
                        onClick={async () => {
                          try {
                            setBusy(true)
                            const r = await api.waSetPhone<WebhookResponse & { phone: string }>(phoneDraft)
                            setPhone(r.phone); setState(r.state)
                            setBubbles((prev) => [...prev,
                              ...(r.messages ?? []).map((m) => ({ id: m.id, direction: 'OUT' as const, kind: m.kind as Bubble['kind'], payload: m.payload as Bubble['payload'], created_at: m.timestamp }))])
                          } catch (e) { setError(e instanceof Error ? e.message : 'Could not save the number.') } finally { setBusy(false) }
                        }}>Start chat</button>
              </div>
            </div>
          )}
          {bubbles.map((b) => <ChatBubble key={b.id} b={b} onButton={onButton} />)}
          {processing && <TypingBubble />}
        </div>

        {/* composer */}
        <div className="wa-composer">
          <button className="wa-round" onClick={attachPhoto} disabled={busy || needsPhone}
                  title="Attach a product photo" aria-label="Attach a product photo">📎</button>
          <button className="wa-round" onClick={recordVoice} disabled={busy || needsPhone}
                  title="Record a voice note" aria-label="Record a voice note">🎙️</button>
          <input className="wa-input" value={draft} placeholder="Type a message"
                 onChange={(e) => setDraft(e.target.value)}
                 onKeyDown={(e) => { if (e.key === 'Enter') onText() }}
                 disabled={busy || needsPhone} aria-label="Type a message" />
          <button className="wa-round send" onClick={onText} disabled={busy || needsPhone || !draft.trim()}
                  title="Send" aria-label="Send message">➤</button>
        </div>
      </div>

      {error && <div className="k-error wa-error" role="alert">{error}</div>}
      <p className="muted small wa-footnote">
        Simulator prototype: this chat drives the same backend pipeline as the main app —
        photo enhancement, multilingual voice transcription, AI catalogue copy and price
        suggestion all happen server-side. A real WhatsApp Business number swaps in behind
        the same webhook without changing this flow.
      </p>
    </div>
  )
}

function ChatBubble({ b, onButton }: { b: Bubble; onButton: (b: { id: string; title: string }) => void }) {
  const out = b.direction === 'OUT'
  if (b.kind === 'image') {
    return (
      <div className={`wa-row ${out ? 'out' : 'in'}`}>
        <div className="wa-bubble image">
          {b.payload.link ? <img src={b.payload.link} alt={b.payload.caption || 'product photo'} /> : <div className="wa-photo-placeholder">📷 photo</div>}
          {b.payload.caption && <div className="wa-caption">{b.payload.caption}</div>}
          <div className="wa-time">{clockLabel(b.created_at)}</div>
        </div>
      </div>
    )
  }
  if (b.kind === 'voice') {
    const bars = waveform(b.id)
    const secs = b.payload.duration_seconds ?? 3
    return (
      <div className={`wa-row ${out ? 'out' : 'in'}`}>
        <div className="wa-bubble voice">
          <button className="wa-play" aria-label="Play voice note">▶</button>
          <div className="wa-wave" aria-hidden>{bars.map((h, i) => <span key={i} style={{ height: h }} />)}</div>
          <div className="wa-dur">{secs}s</div>
          <div className="wa-time">{clockLabel(b.created_at)}</div>
        </div>
      </div>
    )
  }
  if (b.kind === 'interactive') {
    return (
      <div className={`wa-row ${out ? 'out' : 'in'}`}>
        <div className="wa-bubble interactive">
          <div className="wa-body">{b.payload.body}</div>
          {b.payload.ai_tag && <div className="wa-ai-tag">✦ AI suggestion — tap to approve or edit</div>}
          <div className="wa-buttons">
            {(b.payload.buttons ?? []).map((btn) => (
              <button key={btn.id} className="wa-pill" disabled={b.used}
                      onClick={() => onButton(btn)}>{btn.title}</button>
            ))}
          </div>
          <div className="wa-time">{clockLabel(b.created_at)}</div>
        </div>
      </div>
    )
  }
  // text (with any /product/<id> mention rendered as a real link)
  const body = b.payload.body ?? ''
  return (
    <div className={`wa-row ${out ? 'out' : 'in'}`}>
      <div className="wa-bubble text">
        <div className="wa-body">
          {formatBody(body)}
        </div>
        <div className="wa-time">{clockLabel(b.created_at)}</div>
      </div>
    </div>
  )
}

/** WhatsApp-style *bold* rendering + link to a published product mention. */
function formatBody(body: string) {
  const parts = body.split(/(\*[^*]+\*)/g)
  return parts.map((p, i) => {
    if (p.startsWith('*') && p.endsWith('*') && p.length > 2) {
      return <strong key={i}>{p.slice(1, -1)}</strong>
    }
    // Turn a bare "/product/<id>" mention into a real link.
    const m = p.match(/\/product\/([a-z0-9-]+)/i)
    if (m) {
      const before = p.slice(0, m.index)
      const after = p.slice((m.index ?? 0) + m[0].length)
      return (
        <span key={i}>
          {before}
          <Link className="wa-link" to={`/product/${m[1]}`}>View your live listing</Link>
          {after}
        </span>
      )
    }
    return <span key={i}>{p}</span>
  })
}

function TypingBubble() {
  return (
    <div className="wa-row in">
      <div className="wa-bubble text typing" aria-label="Assistant is typing">
        <span className="wa-dot" /><span className="wa-dot" /><span className="wa-dot" />
      </div>
    </div>
  )
}
