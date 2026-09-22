/** Buyer marketplace: natural-language search with visible interpretation. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, serverUrl } from '../../core/api'
import { inr, type ProductSummary } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KInput } from '../../design'
import { useT } from '../../i18n'
import { useUi } from '../../state/stores'
import { listen, sttSupported, speak, type ListenHandle } from '../../voice/voice'
import { useRef } from 'react'

interface Feed {
  items: ProductSummary[]
  total: number
  interpreted: Record<string, unknown> | null
}

export default function ExplorePage() {
  const { t } = useT()
  const lang = useUi((s) => s.lang)
  const [q, setQ] = useState('')
  const [feed, setFeed] = useState<Feed | null>(null)
  const [loading, setLoading] = useState(true)
  const [voiceListening, setVoiceListening] = useState(false)
  const micHandle = useRef<ListenHandle | null>(null)

  const startVoiceSearch = () => {
    if (!sttSupported()) return
    const h = listen({
      lang,
      onFinal: (txt) => {
        setQ(txt)
        setVoiceListening(false)
        speak(t('search.understood_as'), lang)
        void search(txt)
      },
      onError: () => setVoiceListening(false),
      onEnd: () => setVoiceListening(false),
    })
    if (h) micHandle.current = h
  }

  async function search(query = q) {
    setLoading(true)
    try {
      setFeed(await api.get<Feed>(`/products?q=${encodeURIComponent(query)}`))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void search('') /* eslint-disable-line react-hooks/exhaustive-deps */ }, [])

  return (
    <div className="k-stack" style={{ paddingBottom: 40 }}>
      <div>
        <h1 style={{ fontSize: 24 }}>{t('explore.title')}</h1>
        <div className="muted small">{t('explore.subtitle')}</div>
      </div>

      <div className="k-row">
        <KInput style={{ flex: 1 }}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter') void search() }}
                placeholder={t('search.placeholder')} />
        <KButton onClick={() => void search()}>{t('search.button')}</KButton>
        {sttSupported() && (
          <button
            className={`k-mic-btn ${voiceListening ? 'listening' : ''}`}
            style={{ width: 52, height: 52 }}
            onClick={startVoiceSearch}
            aria-label={t('explore.voice_search')}
          >
            <span className="k-mic-icon" style={{ fontSize: 22 }} aria-hidden>🎤</span>
          </button>
        )}
      </div>
      {voiceListening && <div className="muted small" aria-live="polite">🎙️ {t('home.listening')}</div>}

      {feed?.interpreted && (
        <div className="k-row">
          <span className="muted small">{t('search.understood_as')}</span>
          {Object.entries(feed.interpreted).map(([k, v]) => (
            <KBadge key={k} tone="blue">{k.replace('_', ' ')}: {String(v)}</KBadge>
          ))}
        </div>
      )}

      {loading && <div className="k-grid">{[1, 2, 3, 4].map((i) => <KCard key={i}><div className="k-skeleton" style={{ height: 220 }} /></KCard>)}</div>}

      {feed && feed.items.length === 0 && !loading && (
        <KCard><KEmpty icon="🔍" title={t('search.no_results')}
                       hint={t('search.no_results_hint')} /></KCard>
      )}

      {feed && feed.items.length > 0 && (
        <div className="k-grid">
          {feed.items.map((p) => (
            <Link key={p.id} to={`/product/${p.id}`}>
              <KCard className="k-product-card">
                {p.image_url ? <img className="ph" src={serverUrl(p.image_url)} alt={p.title} loading="lazy" /> : <div className="ph" />}
                <div className="body">
                  <strong style={{ fontSize: 14.5 }}>{p.title}</strong>
                  <span className="muted small">{p.material}{p.technique ? ` · ${p.technique}` : ''}</span>
                  <div className="k-spread" style={{ marginTop: 'auto' }}>
                    <span className="k-price">{inr(p.price)}</span>
                    <span className="k-row" style={{ gap: 4 }}>
                      {p.customization_available && <KBadge tone="violet">custom</KBadge>}
                      {p.bulk_moq && <KBadge tone="gold">bulk</KBadge>}
                    </span>
                  </div>
                </div>
              </KCard>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
