/** Checkout: address → demo payment (server-verified) → relationship screen.
 *  Honesty rules enforced here: payment success comes from the settle response,
 *  reviews unlock only for delivered/completed orders, reorder is a real API. */

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type OrderView } from '../../core/types'
import { KBadge, KButton, KCard, KError, KInput, KLabel, KSkeleton } from '../../design'
import { useAuth } from '../../state/stores'

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

  useEffect(() => {
    if (!user) { navigate('/login', { replace: true }); return }
    const savedAddr = localStorage.getItem('karvantana.address')
    if (savedAddr) { try { setAddress(JSON.parse(savedAddr)) } catch { /* ignore */ } }
    api.get<OrderView>(`/orders/${id}`).then(setOrder).catch((e) => setError(e instanceof Error ? e.message : 'Order not found.'))
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
      setError(e instanceof Error ? e.message : 'Payment failed. Please try again.')
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
      setError(e instanceof Error ? e.message : 'Review could not be saved.')
    } finally { setBusy(false) }
  }

  async function reorder() {
    if (!order) return
    setBusy(true); setError('')
    try {
      const next = await api.post<{ id: string; order_number: string }>(`/orders/${order.id}/reorder`)
      setReordered(next.order_number)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Some items are no longer available to reorder.')
    } finally { setBusy(false) }
  }

  async function saveArtisan() {
    if (!item?.artisan_id) return
    setBusy(true); setError('')
    try {
      await api.post(`/artisans/${item.artisan_id}/save`)
      setSaved(true)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save the artisan.')
    } finally { setBusy(false) }
  }

  if (error && !order) return <div className="container" style={{ padding: 40 }}><KError message={error} /></div>
  if (!order) return <div className="container" style={{ padding: 40 }}><KSkeleton h={220} /></div>

  const paidAlready = order.status !== 'PENDING_PAYMENT' && order.status !== 'DRAFT'

  return (
    <div className="container" style={{ maxWidth: 640, padding: '24px 20px 80px' }}>
      <div className="k-stack">
        <div className="k-spread">
          <h2 style={{ fontSize: 22 }}>Checkout</h2>
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
          <div className="k-spread"><span className="muted small">Platform fee</span><span className="muted small">{inr(order.platform_fee)}</span></div>
          <div className="k-spread"><strong>Total</strong><strong className="k-price">{inr(order.total)}</strong></div>
        </KCard>

        {!paidAlready && (
          <>
            <KCard>
              <h3>Delivery address</h3>
              <KLabel>Address</KLabel>
              <KInput value={address.line1} onChange={(e) => setAddress({ ...address, line1: e.target.value })} placeholder="House / street" />
              <div className="k-row">
                <div style={{ flex: 1 }}><KLabel>City</KLabel>
                  <KInput value={address.city} onChange={(e) => setAddress({ ...address, city: e.target.value })} /></div>
                <div style={{ flex: 1 }}><KLabel>PIN code</KLabel>
                  <KInput value={address.pincode} onChange={(e) => setAddress({ ...address, pincode: e.target.value })} inputMode="numeric" /></div>
              </div>
            </KCard>

            <KCard>
              <div className="k-spread">
                <h3>Payment</h3>
                <KBadge tone="gold">Demo provider — sandbox</KBadge>
              </div>
              <p className="muted small">
                This deployment uses the clearly-labeled DemoPaymentProvider. Orders settle only after the
                server verifies the gateway webhook — client "success" is never trusted.
              </p>
              {intent && <p className="muted small">Intent <code>{intent.provider_payment_id}</code> created with {intent.provider}.</p>}
              <KButton block size="lg" onClick={pay} disabled={busy || !address.line1 || !address.pincode}>
                {busy ? 'Verifying payment…' : `Pay ${inr(order.total)} (demo)`}
              </KButton>
            </KCard>
          </>
        )}

        {paidAlready && (
          <>
            {paid && <div className="k-ok" role="status">✓ Payment verified — your order is confirmed. {item?.title && <>You're buying directly from the maker of {item.title}.</>}</div>}

            <KCard className="pad-lg k-weave">
              <h3>Build the relationship</h3>
              <p className="muted small">Marketplaces connect you to products. KARVANTANA connects you back to the artisan.</p>
              <div className="k-row" style={{ marginTop: 12 }}>
                <KButton size="sm" variant="ghost" onClick={() => void reorder()} disabled={busy}>🔁 Buy again anytime</KButton>
                <KButton size="sm" variant="ghost" onClick={saveArtisan} disabled={busy || saved}>
                  {saved ? '✓ Artisan saved' : '➕ Save this artisan'}
                </KButton>
                <Link to="/buyer/orders" className="k-btn sm ghost">Track your orders</Link>
              </div>
              {reordered && (
                <div className="k-ok" style={{ marginTop: 10 }}>
                  Reorder created: {reordered} — repeat business starts here.
                </div>
              )}
            </KCard>

            {canReview && !reviewDone && (
              <KCard>
                <h3>Rate your experience</h3>
                <p className="muted small">Only verified purchases can be reviewed.</p>
                <KInput value={review} onChange={(e) => setReview(e.target.value)} placeholder="Say something honest — it helps other buyers trust handmade." />
                <div style={{ marginTop: 10 }}><KButton variant="ghost" onClick={submitReview} disabled={busy}>Submit 5★ review</KButton></div>
              </KCard>
            )}
            {canReview && reviewDone && <div className="k-ok">Thank you — your verified review builds artisan reputation.</div>}
            {!canReview && (
              <p className="muted small">
                Reviews unlock once the order is delivered. Track progress in <Link to="/buyer/orders">your orders</Link>.
              </p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
