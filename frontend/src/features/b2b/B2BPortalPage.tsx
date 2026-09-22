/** B2B portal: describe a procurement need in plain language → the server's AI
 *  parses it → matched products with explainable reasons → per-artisan quotes
 *  → accept a quote → a real, payable order. */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, serverUrl } from '../../core/api'
import { inr, type BulkRequestView, type QuoteView } from '../../core/types'
import { KAIStages, KBadge, KButton, KCard, KEmpty, KError, KInput, KLabel, KSkeleton, KTextarea } from '../../design'
import { useT } from '../../i18n'

interface Match {
  product_id: string
  title: string
  image_url: string | null
  price: number
  bulk_price: number | null
  bulk_moq: number | null
  artisan_id: string
  score: number
  reasons: string[]
}

export default function B2BPortalPage() {
  const { t } = useT()

  const [description, setDescription] = useState('')
  const [quantity, setQuantity] = useState('50')
  const [maxPrice, setMaxPrice] = useState('')
  const [requiredBy, setRequiredBy] = useState('')
  const [needsCustom, setNeedsCustom] = useState(false)
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState('')

  const [requests, setRequests] = useState<BulkRequestView[] | null>(null)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [matches, setMatches] = useState<Match[] | null>(null)
  const [quotes, setQuotes] = useState<QuoteView[] | null>(null)
  const [accepted, setAccepted] = useState<{ order_number: string; order_id: string } | null>(null)
  const [busy, setBusy] = useState(false)

  const loadRequests = useCallback(() => {
    api.get<{ items: BulkRequestView[] }>('/bulk-requests/mine')
      .then((r) => setRequests(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : t('b2b.load_failed')))
  }, [t])

  useEffect(() => { loadRequests() }, [loadRequests])

  async function openRequest(id: string) {
    setActiveId(id); setMatches(null); setQuotes(null); setAccepted(null); setError('')
    setBusy(true)
    try {
      const m = await api.get<{ matches: Match[] }>(`/bulk-requests/${id}/matches`)
      setMatches(m.matches)
      const q = await api.get<{ items: QuoteView[] }>('/quotes/mine')
      setQuotes(q.items.filter((x) => x.request_id === id))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('b2b.load_one_failed'))
    } finally { setBusy(false) }
  }

  async function submitRequirement() {
    setParsing(true); setError(''); setMatches(null); setQuotes(null); setAccepted(null)
    try {
      const res = await api.post<{ id: string; parsed: BulkRequestView['parsed'] }>('/bulk-requests', {
        title: description.slice(0, 80) || 'Procurement requirement',
        description,
        quantity: Math.max(2, Number(quantity) || 2),
        max_unit_price: maxPrice ? Number(maxPrice) : undefined,
        required_by: requiredBy || undefined,
        customization_required: needsCustom,
      })
      loadRequests()
      setActiveId(res.id)
      const m = await api.get<{ matches: Match[] }>(`/bulk-requests/${res.id}/matches`)
      setMatches(m.matches)
      const q = await api.get<{ items: QuoteView[] }>('/quotes/mine')
      setQuotes(q.items.filter((x) => x.request_id === res.id))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('b2b.parse_failed'))
    } finally { setParsing(false) }
  }

  async function accept(quoteId: string) {
    setBusy(true); setError('')
    try {
      const res = await api.post<{ order_id: string; order_number: string }>(`/quotes/${quoteId}/accept`, {
        shipping_address: JSON.parse(localStorage.getItem('karvantana.address') ?? '{"line1":"","city":"","pincode":""}'),
      })
      setAccepted({ order_number: res.order_number, order_id: res.order_id })
      loadRequests()
      if (activeId) {
        const q = await api.get<{ items: QuoteView[] }>('/quotes/mine')
        setQuotes(q.items.filter((x) => x.request_id === activeId))
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : t('b2b.accept_failed'))
    } finally { setBusy(false) }
  }

  const active = requests?.find((r) => r.id === activeId) ?? null

  return (
    <div className="container" style={{ padding: '24px 20px 90px', maxWidth: 880 }}>
      <div className="k-stack">
        <div className="k-spread">
          <div>
            <h2 style={{ fontSize: 22 }}>{t('b2b.title')}</h2>
            <div className="muted small">{t('b2b.subtitle')}</div>
          </div>
          <Link to="/explore" className="k-btn sm ghost">{t('b2b.browse')}</Link>
        </div>

        {error && <KError message={error} />}
        {accepted && (
          <div className="k-ok" role="status">
            {t('b2b.quote_accepted')} {accepted.order_number}.{' '}
            <Link to={`/checkout/${accepted.order_id}`} style={{ textDecoration: 'underline' }}>{t('order.complete_payment')} →</Link>
          </div>
        )}

        <KCard>
          <h3>{t('b2b.new_req')}</h3>
          <KLabel>{t('b2b.what_need')}</KLabel>
          <KTextarea value={description} onChange={(e) => setDescription(e.target.value)}
                     placeholder='e.g. "500 handmade corporate gift boxes, natural materials, under ₹400 each, delivery within 30 days, logo engraving preferred"' />
          <div className="k-row" style={{ marginTop: 10 }}>
            <div style={{ width: 110 }}><KLabel>{t('b2b.quantity')}</KLabel>
              <KInput value={quantity} onChange={(e) => setQuantity(e.target.value)} inputMode="numeric" /></div>
            <div style={{ width: 150 }}><KLabel>{t('b2b.max_price')}</KLabel>
              <KInput value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} inputMode="decimal" placeholder="optional" /></div>
            <div style={{ width: 170 }}><KLabel>{t('b2b.needed_by')}</KLabel>
              <KInput type="date" value={requiredBy} onChange={(e) => setRequiredBy(e.target.value)} /></div>
          </div>
          <label className="k-row small" style={{ marginTop: 10, cursor: 'pointer' }}>
            <input type="checkbox" checked={needsCustom} onChange={(e) => setNeedsCustom(e.target.checked)} />
            {t('b2b.customization')}
          </label>
          <div style={{ marginTop: 14 }}>
            <KButton size="lg" onClick={submitRequirement} disabled={parsing || description.trim().length < 10}>
              {parsing ? t('b2b.parsing') : `✨ ${t('b2b.parse_find')}`}
            </KButton>
          </div>
          {parsing && (
            <div style={{ marginTop: 14 }}>
              <KAIStages stages={[
                { label: 'Requirement received', state: 'done' },
                { label: 'Extracting quantity, budget & category', state: 'active' },
                { label: 'Matching artisan capacity', state: 'pending' },
              ]} />
            </div>
          )}
        </KCard>

        {active && (
          <KCard className="k-weave">
            <div className="k-spread">
              <h3>{active.title}</h3>
              <KBadge tone="blue">{active.status}</KBadge>
            </div>
            {active.parsed && (
              <div className="k-row" style={{ margin: '8px 0 12px' }}>
                <span className="muted small">{t('b2b.ai_understood')}</span>
                {Object.entries(active.parsed)
                  .filter(([k]) => k !== 'confidence')
                  .map(([k, v]) => <KBadge key={k} tone="violet">{k.replace(/_/g, ' ')}: {String(v)}</KBadge>)}
              </div>
            )}
            <div className="muted small">
              Requested {active.quantity} units{active.max_unit_price ? ` · up to ${inr(active.max_unit_price)}/unit` : ''}
            </div>
          </KCard>
        )}

        {busy && matches === null && <KSkeleton h={120} />}

        {matches && matches.length > 0 && (
          <div className="k-stack">
            <h3 style={{ margin: 0 }}>{t('b2b.matched')}</h3>
            {matches.map((m) => (
              <KCard key={m.product_id}>
                <div className="k-spread">
                  <div className="k-row">
                    {m.image_url && <img src={serverUrl(m.image_url)} alt="" style={{ width: 64, height: 64, borderRadius: 12, objectFit: 'cover' }} />}
                    <div>
                      <Link to={`/product/${m.product_id}`} style={{ fontWeight: 700 }}>{m.title}</Link>
                      <div className="muted small">
                        {inr(m.price)}{m.bulk_price ? ` · ${inr(m.bulk_price)}/unit at ${m.bulk_moq}+` : ''}
                      </div>
                      <div className="k-row" style={{ marginTop: 6 }}>
                        <KBadge tone="blue">{t('b2b.match')} {Math.round(m.score * 100)}%</KBadge>
                        {m.reasons.slice(0, 2).map((r) => <span key={r} className="muted small">✓ {r}</span>)}
                      </div>
                    </div>
                  </div>
                  <Link to={`/artisan-u/${m.artisan_id}`} className="k-btn sm ghost">{t('b2b.view_artisan')}</Link>
                </div>
              </KCard>
            ))}
          </div>
        )}
        {matches && matches.length === 0 && active && (
          <KEmpty icon="🧭" title={t('b2b.no_matches')}
                  hint={t('b2b.no_matches_hint')} />
        )}

        {quotes && quotes.length > 0 && (
          <div className="k-stack">
            <h3 style={{ margin: 0 }}>{t('b2b.quotes')}</h3>
            {quotes.map((q) => (
              <KCard key={q.id}>
                <div className="k-spread">
                  <div>
                    <strong>{q.artisan}</strong>
                    <div className="muted small">
                      {inr(q.unit_price)}/unit × {q.quantity} = <strong>{inr(q.total)}</strong> · {q.lead_time_days} {t('b2b.day_lead')}
                      {q.note ? ` · "${q.note}"` : ''}
                    </div>
                  </div>
                  {q.status === 'PENDING'
                    ? <KButton onClick={() => void accept(q.id)} disabled={busy}>{t('b2b.accept_quote')}</KButton>
                    : <KBadge tone={q.status === 'ACCEPTED' ? 'green' : 'gold'}>{q.status}</KBadge>}
                </div>
              </KCard>
            ))}
          </div>
        )}

        {requests && requests.length > 0 && (
          <div className="k-stack">
            <h3 style={{ margin: 0 }}>{t('b2b.your_reqs')}</h3>
            {requests.map((r) => (
              <KCard key={r.id} className={r.id === activeId ? 'k-weave' : ''}>
                <div className="k-spread">
                  <div>
                    <div className="k-row"><strong>{r.title}</strong><KBadge tone="blue">{r.status}</KBadge></div>
                    <div className="muted small">
                      {r.quantity} units · {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </div>
                  </div>
                  <KButton size="sm" variant="ghost" onClick={() => void openRequest(r.id)}>{t('b2b.open_pipeline')}</KButton>
                </div>
              </KCard>
            ))}
          </div>
        )}

        {requests && requests.length === 0 && (
          <KEmpty icon="📦" title={t('b2b.none_yet')}
                  hint={t('b2b.none_hint')} />
        )}

        <p className="muted small">
          Tip: use the <Link to="/buyer/orders" style={{ textDecoration: 'underline' }}>orders page</Link> to track
          fulfilment. Payment settles only after server-side verification.
        </p>
      </div>
    </div>
  )
}
