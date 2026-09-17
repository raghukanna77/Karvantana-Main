/** B2B portal: describe a procurement need in plain language → the server's AI
 *  parses it → matched products with explainable reasons → per-artisan quotes
 *  → accept a quote → a real, payable order. */

import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type BulkRequestView, type QuoteView } from '../../core/types'
import { KAIStages, KBadge, KButton, KCard, KEmpty, KError, KInput, KLabel, KSkeleton, KTextarea } from '../../design'
import { useAuth } from '../../state/stores'

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
  const user = useAuth((s) => s.user)

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
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load requests.'))
  }, [])

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
      setError(e instanceof Error ? e.message : 'Could not load this request.')
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
      setError(e instanceof Error ? e.message : 'Could not process the requirement.')
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
      setError(e instanceof Error ? e.message : 'Could not accept the quote.')
    } finally { setBusy(false) }
  }

  const active = requests?.find((r) => r.id === activeId) ?? null

  return (
    <div className="container" style={{ padding: '24px 20px 90px', maxWidth: 880 }}>
      <div className="k-stack">
        <div className="k-spread">
          <div>
            <h2 style={{ fontSize: 22 }}>Procurement workspace</h2>
            <div className="muted small">
              {user ? `Business account · ${user.full_name}` : 'Sign in to manage procurement'} — every order goes directly to the artisan collective.
            </div>
          </div>
          <Link to="/explore" className="k-btn sm ghost">Browse catalogue</Link>
        </div>

        {error && <KError message={error} />}
        {accepted && (
          <div className="k-ok" role="status">
            ✓ Quote accepted — order {accepted.order_number} created.{' '}
            <Link to={`/checkout/${accepted.order_id}`} style={{ textDecoration: 'underline' }}>Complete payment →</Link>
          </div>
        )}

        <KCard>
          <h3>New procurement requirement</h3>
          <KLabel>What do you need? (plain language — the AI structures it)</KLabel>
          <KTextarea value={description} onChange={(e) => setDescription(e.target.value)}
                     placeholder='e.g. "500 handmade corporate gift boxes, natural materials, under ₹400 each, delivery within 30 days, logo engraving preferred"' />
          <div className="k-row" style={{ marginTop: 10 }}>
            <div style={{ width: 110 }}><KLabel>Quantity</KLabel>
              <KInput value={quantity} onChange={(e) => setQuantity(e.target.value)} inputMode="numeric" /></div>
            <div style={{ width: 150 }}><KLabel>Max ₹ / unit</KLabel>
              <KInput value={maxPrice} onChange={(e) => setMaxPrice(e.target.value)} inputMode="decimal" placeholder="optional" /></div>
            <div style={{ width: 170 }}><KLabel>Needed by</KLabel>
              <KInput type="date" value={requiredBy} onChange={(e) => setRequiredBy(e.target.value)} /></div>
          </div>
          <label className="k-row small" style={{ marginTop: 10, cursor: 'pointer' }}>
            <input type="checkbox" checked={needsCustom} onChange={(e) => setNeedsCustom(e.target.checked)} />
            Customization required (branding, sizes, packaging…)
          </label>
          <div style={{ marginTop: 14 }}>
            <KButton size="lg" onClick={submitRequirement} disabled={parsing || description.trim().length < 10}>
              {parsing ? 'Parsing requirement…' : '✨ Parse & find artisans'}
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
                <span className="muted small">AI understood:</span>
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
            <h3 style={{ margin: 0 }}>Matched products</h3>
            {matches.map((m) => (
              <KCard key={m.product_id}>
                <div className="k-spread">
                  <div className="k-row">
                    {m.image_url && <img src={m.image_url} alt="" style={{ width: 64, height: 64, borderRadius: 12, objectFit: 'cover' }} />}
                    <div>
                      <Link to={`/product/${m.product_id}`} style={{ fontWeight: 700 }}>{m.title}</Link>
                      <div className="muted small">
                        {inr(m.price)}{m.bulk_price ? ` · ${inr(m.bulk_price)}/unit at ${m.bulk_moq}+` : ''}
                      </div>
                      <div className="k-row" style={{ marginTop: 6 }}>
                        <KBadge tone="blue">match {Math.round(m.score * 100)}%</KBadge>
                        {m.reasons.slice(0, 2).map((r) => <span key={r} className="muted small">✓ {r}</span>)}
                      </div>
                    </div>
                  </div>
                  <Link to={`/artisan-u/${m.artisan_id}`} className="k-btn sm ghost">View artisan</Link>
                </div>
              </KCard>
            ))}
          </div>
        )}
        {matches && matches.length === 0 && active && (
          <KEmpty icon="🧭" title="No in-catalogue matches yet"
                  hint="Your requirement is saved — artisans see it in their opportunity feed and will quote directly." />
        )}

        {quotes && quotes.length > 0 && (
          <div className="k-stack">
            <h3 style={{ margin: 0 }}>Quotes</h3>
            {quotes.map((q) => (
              <KCard key={q.id}>
                <div className="k-spread">
                  <div>
                    <strong>{q.artisan}</strong>
                    <div className="muted small">
                      {inr(q.unit_price)}/unit × {q.quantity} = <strong>{inr(q.total)}</strong> · {q.lead_time_days}-day lead
                      {q.note ? ` · "${q.note}"` : ''}
                    </div>
                  </div>
                  {q.status === 'PENDING'
                    ? <KButton onClick={() => void accept(q.id)} disabled={busy}>Accept quote</KButton>
                    : <KBadge tone={q.status === 'ACCEPTED' ? 'green' : 'gold'}>{q.status}</KBadge>}
                </div>
              </KCard>
            ))}
          </div>
        )}

        {requests && requests.length > 0 && (
          <div className="k-stack">
            <h3 style={{ margin: 0 }}>Your requirements</h3>
            {requests.map((r) => (
              <KCard key={r.id} className={r.id === activeId ? 'k-weave' : ''}>
                <div className="k-spread">
                  <div>
                    <div className="k-row"><strong>{r.title}</strong><KBadge tone="blue">{r.status}</KBadge></div>
                    <div className="muted small">
                      {r.quantity} units · {new Date(r.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </div>
                  </div>
                  <KButton size="sm" variant="ghost" onClick={() => void openRequest(r.id)}>Open pipeline</KButton>
                </div>
              </KCard>
            ))}
          </div>
        )}

        {requests && requests.length === 0 && (
          <KEmpty icon="📦" title="No procurement requirements yet"
                  hint="Describe what your business needs above — KARVANTANA structures it and routes it to capable artisan clusters." />
        )}

        <p className="muted small">
          Tip: use the <Link to="/buyer/orders" style={{ textDecoration: 'underline' }}>orders page</Link> to track
          fulfilment. Payment settles only after server-side verification.
        </p>
      </div>
    </div>
  )
}
