/** Product page — the artisan is always front and centre. */

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api, serverUrl } from '../../core/api'
import { inr, type ProductDetail } from '../../core/types'
import { KBadge, KButton, KCard, KError, KInput, KTextarea } from '../../design'
import { useAuth } from '../../state/stores'
import { useT } from '../../i18n'
import AddressForm, { type Address } from './AddressForm'

export default function ProductPage() {
  const { id = '' } = useParams()
  const [p, setP] = useState<ProductDetail | null>(null)
  const [error, setError] = useState('')
  const [qty, setQty] = useState(1)
  const [busy, setBusy] = useState(false)
  const [customOpen, setCustomOpen] = useState(false)
  const [customTitle, setCustomTitle] = useState('')
  const [customNote, setCustomNote] = useState('')
  const [customDone, setCustomDone] = useState(false)
  const [addressOpen, setAddressOpen] = useState(false)
  const user = useAuth((s) => s.user)
  const navigate = useNavigate()
  const { t } = useT()

  async function load() {
    try { setP(await api.get<ProductDetail>(`/products/${id}`)) }
    catch (e) { setError(e instanceof Error ? e.message : t('pp.load_failed')) }
  }
  useEffect(() => { void load() /* eslint-disable-line react-hooks/exhaustive-deps */ }, [id])

  async function buy() {
    if (!user) { navigate('/login', { state: { from: `/product/${id}` } }); return }
    setBusy(true); setError('')
    try {
      const saved: Address | null = (() => {
        try { return JSON.parse(localStorage.getItem('karvantana.address') ?? 'null') as Address | null }
        catch { return null }
      })()
      let address = saved && saved.line1 && saved.pincode ? saved : null
      if (!address) {
        setBusy(false)
        setAddressOpen(true)
        return
      }
      const order = await api.post<{ id: string; order_number: string }>('/orders',
        {
          items: [{ product_id: id, quantity: qty }],
          shipping_address: { line1: address.line1, city: address.city, pincode: address.pincode },
        },
        `order-${id}-${Date.now()}`)
      navigate(`/checkout/${order.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('pp.buy_failed'))
    } finally { setBusy(false) }
  }

  function buyWithAddress(a: Address) {
    localStorage.setItem('karvantana.address', JSON.stringify(a))
    void buy()
  }

  async function requestCustom() {
    if (!user) { navigate('/login'); return }
    if (!p?.artisan) return
    setBusy(true); setError('')
    try {
      await api.post('/custom-requests', {
        artisan_id: p.artisan.id, title: customTitle || `Custom request — ${p.title}`,
        description: customNote, quantity: qty, product_id: p.id,
      })
      setCustomDone(true); setCustomOpen(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('pp.custom_failed'))
    } finally { setBusy(false) }
  }

  if (error && !p) return <div className="container" style={{ padding: 40 }}><KError message={error} /></div>
  if (!p) return <div className="container" style={{ padding: 40 }}><div className="k-skeleton" style={{ height: 300 }} /></div>

  return (
    <div className="k-stack" style={{ paddingBottom: 60 }}>
      <div className="k-grid" style={{ gridTemplateColumns: 'minmax(240px, 460px) 1fr', alignItems: 'start' }}>
        <div>
          {p.image_url
            ? <img src={serverUrl(p.image_url)} alt={p.title} style={{ borderRadius: 20, width: '100%' }} />
            : <div style={{ aspectRatio: '1', borderRadius: 20, background: 'var(--navy-700)' }} />}
        </div>

        <div className="k-stack">
          <div className="k-row">
            {p.technique && <KBadge tone="blue">{p.technique}</KBadge>}
            {p.origin && <KBadge tone="gold">{p.origin}</KBadge>}
            {p.customization_available && <KBadge tone="violet">{t('pp.customizable')}</KBadge>}
          </div>
          <h1 style={{ fontSize: 28, lineHeight: 1.15 }}>{p.title}</h1>
          <div className="k-row">
            <span className="k-price" style={{ fontSize: 26 }}>{inr(p.price)}</span>
            {p.bulk_moq && p.bulk_price && (
              <span className="muted small">{inr(p.bulk_price)}/unit {t('pp.bulk_for')} {p.bulk_moq}+ · {t('pp.bulk_friendly')}</span>
            )}
          </div>
          {p.short_description && <p className="muted">{p.short_description}</p>}

          <div className="k-row">
            <div style={{ maxWidth: 110 }}>
              <KInput value={qty} onChange={(e) => setQty(Math.max(1, Number(e.target.value) || 1))} inputMode="numeric" aria-label={t('pp.qty')} />
            </div>
            <KButton size="lg" onClick={buy} disabled={busy || !p.in_stock}>
              {p.in_stock ? `🛍️ ${t('cta.buy_from_artisan')}` : t('pp.out_of_stock')}
            </KButton>
            <KButton variant="ghost" onClick={() => setCustomOpen(!customOpen)}>✨ {t('cta.request_custom')}</KButton>
            {p.bulk_moq && <KButton variant="ghost" onClick={() => navigate('/b2b')}>📦 {t('cta.request_bulk')}</KButton>}
          </div>
          {addressOpen && (
            <KCard>
              <AddressForm
                onSaved={(a: Address) => { setAddressOpen(false); void buyWithAddress(a) }}
                onCancel={() => setAddressOpen(false)}
              />
            </KCard>
          )}

          {customDone && <div className="k-ok">{t('pp.custom_done')}</div>}
          {customOpen && (
            <KCard>
              <KInput value={customTitle} onChange={(e) => setCustomTitle(e.target.value)} placeholder="What do you have in mind?" />
              <KTextarea style={{ marginTop: 8 }} value={customNote} onChange={(e) => setCustomNote(e.target.value)}
                         placeholder="Colours, size, quantity, deadline…" />
              <div style={{ marginTop: 10 }}><KButton onClick={requestCustom} disabled={busy || !customTitle}>Send request</KButton></div>
            </KCard>
          )}

          {error && <KError message={error} />}

          {p.description && (
            <KCard>
              <h3>{t('pp.about')}</h3>
              <p className="muted small" style={{ whiteSpace: 'pre-wrap', marginTop: 8 }}>{p.description}</p>
            </KCard>
          )}

          {/* attributes with confidence */}
          {p.attributes && p.attributes.length > 0 && (
            <KCard>
              <h3>{t('order.details')}</h3>
              <div className="k-stack" style={{ marginTop: 8 }}>
                {p.attributes.filter((a) => a.source !== 'SYSTEM').map((a) => (
                  <div key={a.key} className="k-spread">
                    <span className="muted small" style={{ textTransform: 'capitalize' }}>{a.key.replace('_', ' ')}</span>
                    <span className="k-row" style={{ gap: 8 }}>
                      <strong style={{ textTransform: 'capitalize' }}>{a.value}</strong>
                      {a.confidence < 0.75 && <KBadge tone="gold">{t('pp.artisan_confirmed')}</KBadge>}
                    </span>
                  </div>
                ))}
              </div>
            </KCard>
          )}
        </div>
      </div>

      {/* ARTISAN — the person behind the product */}
      {p.artisan && (
        <KCard className="pad-lg k-weave">
          <div className="k-spread">
            <div className="k-row">
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(135deg, var(--blue), var(--violet))', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 20 }}>
                {p.artisan.display_name.charAt(0)}
              </div>
              <div>
                <div className="k-row">
                  <strong style={{ fontSize: 17 }}>{p.artisan.display_name}</strong>
                  <KBadge tone="green">{p.artisan.verification_level.replace(/_/g, ' ')}</KBadge>
                </div>
                <div className="muted small">{p.artisan.craft} · {p.artisan.location}</div>
                <div className="muted small">
                  {p.artisan.stats.rating ? `${p.artisan.stats.rating}★ (${p.artisan.stats.rating_count}) · ` : ''}
                  {p.artisan.stats.verified_orders} {t('profile.verified_orders')} · {p.artisan.stats.repeat_buyers} {t('profile.repeat_buyers')}
                </div>
              </div>
            </div>
          </div>
          {p.artisan.story && <p className="muted small" style={{ marginTop: 10 }}>{p.artisan.story}</p>}
          {p.artisan.products && p.artisan.products.length > 0 && (
            <>
              <hr className="k-divider" />
              <h3>{t('pp.more_from')}</h3>
              <div className="k-row" style={{ marginTop: 10 }}>
                {p.artisan.products.map((o) => (
                  <Link key={o.id} to={`/product/${o.id}`} className="k-btn sm ghost">{o.title} · {inr(o.price)}</Link>
                ))}
              </div>
            </>
          )}
        </KCard>
      )}

      {p.reviews && p.reviews.length > 0 && (
        <KCard>
          <h3>{t('pp.reviews')}</h3>
          <div className="k-stack" style={{ marginTop: 10 }}>
            {p.reviews.map((r, i) => (
              <div key={i} style={{ borderBottom: '1px dashed var(--stroke)', paddingBottom: 8 }}>
                <div className="k-row">
                  <span>{'★'.repeat(r.rating)}{'☆'.repeat(5 - r.rating)}</span>
                  {r.verified && <KBadge tone="green">{t('pp.verified_purchase')}</KBadge>}
                  <span className="muted small">{r.buyer_name}</span>
                </div>
                {r.text && <div className="small" style={{ marginTop: 4 }}>{r.text}</div>}
              </div>
            ))}
          </div>
        </KCard>
      )}
    </div>
  )
}
