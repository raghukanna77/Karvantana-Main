/** Checkout: address → demo payment (server-verified) → relationship screen.
 *  Honesty rules enforced here: payment success comes from the settle response,
 *  reviews unlock only for delivered/completed orders, reorder is a real API. */

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type OrderView } from '../../core/types'
import { KBadge, KButton, KCard, KError, KInput, KLabel, KSkeleton } from '../../design'
import { useAuth } from '../../state/stores'
import { useT } from '../../i18n'

interface Intent {
  payment_id: string
  provider: string
  provider_payment_id: string
  amount: number
  demo: boolean
}

interface OrderItemFull extends OrderItemLite { artisan_id?: string }
interface OrderItemLite { id: string; product_id: string; title: string; image_url: string | null; unit_price: number; quantity: number; line_total: number }

export default function CheckoutPage() {
  const { id = '' } = useParams()
  const [order, setOrder] = useState<OrderView | null>(null)
  const [address, setAddress] = useState({ line1: '', city: '', state: '', pincode: '' })
  const [intent, setIntent] = useState<Intent | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [paid, setPaid] = useState(false)
  const [review, setReview] = useState('')
  const [reviewDone, setReviewDone] = useState(false)
  const [reordered, setReordered] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)
  const user = useAuth((s) => s.user)
  const navigate = useNavigate()
  const { t } = useT()

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return }
    const savedAddr = localStorage.getItem('karvantana.address')
    if (savedAddr) { try { setAddress(JSON.parse(savedAddr)) } catch { /* ignore */ } }      api.get<OrderView>(`/orders/${id}`).then(setOrder).catch((e) => setError(e instanceof Error ? e.message : t('co.order_not_found')))
  }, [id, user, navigate])

  async function pay() {
    if (!order) return
    setBusy(true); setError('')
    try {
      localStorage.setItem('karvantana.address', JSON.stringify(address))
      const created = await api.post<Intent>('/payments/create-intent', { order_id: order.id }, `intent-${order.id}`)
      setIntent(created)
      // Demo gateway triggers our signature-verified webhook; the server settles
      // the order. We trust only the settle response, never "client success".
      const res = await api.post<{ status: string; order_status?: string }>(
        '/payments/demo/confirm', { provider_payment_id: created.provider_payment_id })
      if (res.order_status !== 'CONFIRMED') throw new Error('Payment could not be verified — you have not been charged.')
      setPaid(true)
      setOrder(await api.get<OrderView>(`/orders/${order.id}`))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('co.pay_failed'))
    } finally { setBusy(false) }
  }

  const item = (order?.items ?? [])[0] as OrderItemFull | undefined
  const canReview = order?.status === 'DELIVERED' || order?.status === 'COMPLETED'

  async function submitReview() {
    if (!order || !item) return
    setBusy(true); setError('')
    try {
      await api.post(`/products/${item.product_id}/reviews`,
        { order_item_id: item.id, product_rating: 5, text: review || undefined })
      setReviewDone(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('co.review_failed'))
    } finally { setBusy(false) }
  }

  async function reorder() {
    if (!order) return
    setBusy(true); setError('')
    try {
      const next = await api.post<{ id: string; order_number: string }>(`/orders/${order.id}/reorder`)
      setReordered(next.order_number)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('co.reorder_failed'))
    } finally { setBusy(false) }
  }

  async function saveArtisan() {
    if (!item?.artisan_id) return
    setBusy(true); setError('')
    try {
      await api.post(`/artisans/${item.artisan_id}/save`)
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('co.save_failed'))
    } finally { setBusy(false) }
  }

  if (error && !order) return <div className="container" style={{ padding: 40 }}><KError message={error} /></div>
  if (!order) return <div className="container" style={{ padding: 40 }}><KSkeleton h={220} /></div>

  const paidAlready = order.status !== 'PENDING_PAYMENT' && order.status !== 'DRAFT'

  return (
    <div className="container" style={{ maxWidth: 640, padding: '24px 20px 80px' }}>
      <div className="k-stack">
        <div className="k-spread">
          <h2 style={{ fontSize: 22 }}>{t('co.title')}</h2>
          <KBadge>{order.order_number}</KBadge>
        </div>
        {error && <KError message={error} />}

        <KCard>
          {order.items.map((i) => (
            <div key={i.id} className="k-spread" style={{ padding: '6px 0' }}>
              <span>{i.title} × {i.quantity}</span><strong>{inr(i.line_total)}</strong>
            </div>
          ))}
          <hr className="k-divider" />
          <div className="k-spread"><span className="muted small">{t('co.platform_fee')}</span><span className="muted small">{inr(order.platform_fee)}</span></div>
          <div className="k-spread"><strong>{t('co.total')}</strong><strong className="k-price">{inr(order.total)}</strong></div>
        </KCard>

        {!paidAlready && (
          <>
            <KCard>
              <h3>{t('addr.title')}</h3>
              <KLabel>{t('addr.line1')}</KLabel>
              <KInput value={address.line1} onChange={(e) => setAddress({ ...address, line1: e.target.value })} placeholder={t('addr.line1_ph')} />
              <div className="k-row">
                <div style={{ flex: 1 }}><KLabel>{t('addr.city')}</KLabel>
                  <KInput value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} /></div>
                <div style={{ flex: 1 }}><KLabel>{t('addr.pincode')}</KLabel>
                  <KInput value={address.pincode} onChange={(e) => setAddress({ ...address, pincode: e.target.value })} inputMode="numeric" /></div>
              </div>
            </KCard>

            <KCard>
              <div className="k-spread">
                <h3>{t('co.payment')}</h3>
                <KBadge tone="gold">{t('co.demo_provider')}</KBadge>
              </div>
              <p className="muted small">{t('co.payment_note')}</p>
              {intent && <p className="muted small">Intent <code>{intent.provider_payment_id}</code> · {intent.provider}</p>}
              <KButton block size="lg" onClick={pay} disabled={busy || !address.line1 || !address.pincode}>
                {busy ? t('co.verifying') : `${t('co.pay')} ${inr(order.total)} (demo)`}
              </KButton>
            </KCard>
          </>
        )}

        {paidAlready && (
          <>
            {paid && <div className="k-ok" role="status">✓ {t('co.payment_verified')}</div>}

            <KCard className="pad-lg k-weave">
              <h3>{t('co.relationship')}</h3>
              <p className="muted small">{t('landing.notmarketplace_b')}</p>
              <div className="k-row" style={{ marginTop: 12 }}>
                <KButton size="sm" variant="ghost" onClick={() => void reorder()} disabled={busy}>🔁 {t('cta.buy_again')}</KButton>
                <KButton size="sm" variant="ghost" onClick={saveArtisan} disabled={busy || saved}>
                  {saved ? `✓ ${t('co.artisan_saved')}` : `➕ ${t('co.save_artisan')}`}
                </KButton>
                <Link to="/buyer/orders" className="k-btn sm ghost">{t('order.all_orders')}</Link>
              </div>
              {reordered && (
                <div className="k-ok" style={{ marginTop: 10 }}>
                  {t('co.reorder_created')}: {reordered}
                </div>
              )}
            </KCard>

            {canReview && !reviewDone && (
              <KCard>
                <h3>{t('co.rate_title')}</h3>
                <p className="muted small">{t('co.rate_note')}</p>
                <KInput value={review} onChange={(e) => setReview(e.target.value)} placeholder={t('co.rate_ph')} />
                <div style={{ marginTop: 10 }}><KButton variant="ghost" onClick={submitReview} disabled={busy}>{t('co.submit_review')}</KButton></div>
              </KCard>
            )}
            {canReview && reviewDone && <div className="k-ok">{t('co.review_thanks')}</div>}
            {!canReview && (
              <p className="muted small">
                {t('co.review_locked')} <Link to="/buyer/orders">{t('order.all_orders')}</Link>.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
