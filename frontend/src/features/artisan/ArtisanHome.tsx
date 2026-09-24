/** Artisan home — SEE → HEAR → SPEAK → CONFIRM home screen.
 *  Icon-led grid (comprehension before reading) + persistent mic that routes
 *  natural speech to the right workflow. All numbers remain real (from the
 *  analytics API); nothing here is simulated. */
import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type ArtisanDashboard } from '../../core/types'
import { KBadge, KCard, KEmpty, KVStat } from '../../design'
import { KVoiceCapture } from '../../design/voice'
import { useAuth, useUi } from '../../state/stores'
import { useT } from '../../i18n'
import { listen, speak, sttSupported, type ListenHandle } from '../../voice/voice'
import { detectIntent, intentConfirmation } from '../../voice/intents'

export default function ArtisanHome() {
  const user = useAuth((s) => s.user)
  const easyMode = useUi((s) => s.easyMode)
  const lang = useUi((s) => s.lang)
  const { t } = useT()
  const navigate = useNavigate()
  const [dash, setDash] = useState<ArtisanDashboard | null>(null)
  const [error, setError] = useState('')
  const [listening, setListening] = useState(false)
  const [heard, setHeard] = useState('')
  const [micErr, setMicErr] = useState('')
  const micHandle = useRef<ListenHandle | null>(null)

  useEffect(() => {
    api.get<ArtisanDashboard>('/analytics/artisan/dashboard')
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : t('err.generic')))
  }, [t])

  const startMic = () => {
    setHeard(''); setMicErr('')
    if (!sttSupported()) { setMicErr(t('home.mic_unsupported')); return }
    const h = listen({
      lang,
      onFinal: (txt) => {
        setHeard(txt)
        const m = detectIntent(txt)
        if (m) {
          speak(intentConfirmation(m), lang)
          setTimeout(() => navigate(m.route), 400)
        } else {
          // No navigation-grade intent — the AI assistant handles open-ended asks.
          speak(t('assistant.fallback_to_open'), lang)
          navigate('/assistant')
        }
      },
      onError: (e) => setMicErr(e.code === 'not-allowed' ? t('err.mic_denied') : t('vc.unavailable')),
      onEnd: () => setListening(false),
    })
    if (h) { micHandle.current = h; setListening(true) }
  }

  const hour = new Date().getHours()
  const greeting = hour < 12 ? t('home.greeting_m') : hour < 17 ? t('home.greeting_a') : t('home.greeting_e')

  const tiles = [
    { icon: '📷', label: t('home.add_product'), to: '/artisan/products/new' },
    { icon: '💬', label: 'Sell on WhatsApp', to: '/artisan/whatsapp' },
    { icon: '📦', label: t('home.orders'), to: '/artisan/orders' },
    { icon: '💰', label: t('home.earnings'), to: '/artisan/insights' },
    { icon: '❤️', label: t('home.customers'), to: '/artisan/customers' },
    { icon: '🔄', label: t('home.repeat'), to: '/artisan/customers' },
    { icon: '🤖', label: t('nav.my_studio'), to: '/assistant' },
  ]

  return (
    <div className="k-stack">
      <div>
        <h1 style={{ fontSize: 26 }}>{greeting}, {user?.full_name?.split(' ')[0] ?? 'Artisan'}</h1>
        <div className="muted small">{t('home.q')}</div>
    </div>

      {/* Persistent assistant mic — the primary interaction */}
      <KCard style={{ textAlign: 'center' }}>
        <button
          className={`k-mic-btn ${listening ? 'listening' : ''}`}
          style={{ width: 96, height: 96, margin: '6px auto 10px' }}
          onClick={startMic}
          aria-label={t('home.listen')}
          aria-pressed={listening}
        >
          <span className="k-mic-icon" aria-hidden>🎤</span>
        </button>
        <div style={{ fontWeight: 800, fontSize: 18 }}>{t('home.listen')}</div>
        <div className="muted small" style={{ marginTop: 2 }}>{t('home.mic_hint')}</div>
        {listening && <div className="small" style={{ marginTop: 8 }} aria-live="polite">🎙️ {t('home.listening')}</div>}
        {heard && !listening && (
          <div className="k-voice-result" style={{ marginTop: 10, textAlign: 'left' }}>
            <div className="muted small">{t('home.heard')}</div>
            <div className="k-voice-transcript">“{heard}”</div>
          </div>
        )}
        {micErr && <div className="k-error" role="alert" style={{ marginTop: 10 }}>{micErr}</div>}
      </KCard>

      {error && <div className="k-error" role="alert">{error}</div>}

      {!dash && !error && <KCard><div className="k-skeleton" style={{ height: 120 }} /></KCard>}

      {dash && (
        <>
          {/* Icon-led primary actions — big icons, short labels */}
          <div className="k-icon-grid">
            {tiles.map((tile) => (
              <a key={tile.label} className="k-icon-tile" href={tile.to} onClick={(e) => { e.preventDefault(); navigate(tile.to) }}>
                <span className="ic" aria-hidden>{tile.icon}</span>
                <span className="lb">{tile.label}</span>
              </a>
            ))}
          </div>

          {dash.totals.orders === 0 ? (
            <KCard>
              <KEmpty icon="🧺" title={t('home.first_product_title')}
                      hint={t('home.first_product_hint')}
                      action={<a href="/artisan/products/new" className="k-btn primary" onClick={(e) => { e.preventDefault(); navigate('/artisan/products/new') }}>{t('home.add_product')}</a>} />
            </KCard>
          ) : (
            <KCard>
              <div className="k-spread"><h3>{t('home.top_products')}</h3><KBadge tone="blue">{t('home.by_units')}</KBadge></div>
              {dash.top_products.length === 0 ? (
                <p className="muted small">{t('home.no_sales_yet')}</p>
              ) : (
                <div className="k-stack" style={{ marginTop: 10 }}>
                  {dash.top_products.map((p) => (
                    <div key={p.title} className="k-spread">
                      <span>{p.title}</span>
                      <span className="muted small">{p.units} {t('home.sold')} · {inr(p.revenue)}</span>
                    </div>
                  ))}
                </div>
              )}
            </KCard>
          )}

          <KCard>
            <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
              <div><KVStat value={inr(dash.totals.month_revenue)} label={t('home.this_month')} /></div>
              <div><KVStat value={dash.today.new_orders} label={t('home.to_act')} /></div>
              <div><KVStat value={dash.today.enquiries} label={t('home.enquiries')} /></div>
              <div><KVStat value={`${dash.totals.repeat_rate}%`} label={t('home.repeat_buyers')} /></div>
            </div>
          </KCard>
        </>
      )}

      {/* Voice guidance for Easy Mode users: the capture widget with confirm/correct */}
      {(easyMode || listening) && (
        <KCard>
          <KVoiceCapture lang={lang} onResult={(txt: string) => {
            const m = detectIntent(txt)
            if (m) navigate(m.route)
            else navigate('/assistant')
          }} />
        </KCard>
      )}
    </div>
  )
}
