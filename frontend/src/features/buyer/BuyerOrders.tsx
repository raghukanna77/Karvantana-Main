/** Buyer orders: lifecycle with human-readable labels, reorder + review actions. */

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type OrderView } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton } from '../../design'
import { useAuth } from '../../state/stores'

export default function BuyerOrders() {
  const [orders, setOrders] = useState<OrderView[] | null>(null)
  const [error, setError] = useState('')
  const [busyId, setBusyId] = useState<string | null>(null)
  const [msg, setMsg] = useState<{ id: string; text: string } | null>(null)
  const user = useAuth((s) => s.user)
  const navigate = useNavigate()

  const load = useCallback(() => {
    api.get<{ items: OrderView[] }>('/orders/mine')
      .then((r) => setOrders(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load orders.'))
  }, [])

  useEffect(() => { if (user) load() }, [user, load])

  async function reorder(id: string) {
    setBusyId(id); setMsg(null); setError('')
    try {
      const next = await api.post<{ id: string; order_number: string }>(`/orders/${id}/reorder`)
      navigate(`/checkout/${next.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reorder failed.')
      setBusyId(null)
    }
  }

  async function advance(o: OrderView) {
    // One-click progression for demo clarity: artisan advances through fulfilment.
    setBusyId(o.id); setMsg(null); setError('')
    try {
      const next: Record<string, string> = {
        CONFIRMED: 'PROCESSING', PROCESSING: 'IN_PRODUCTION', IN_PRODUCTION: 'READY_TO_SHIP',
        READY_TO_SHIP: 'SHIPPED', SHIPPED: 'DELIVERED', DELIVERED: 'COMPLETED',
      }
      const to = next[o.status]
      if (!to) return
      await api.post(`/orders/${o.id}/status`, { status: to })
      setMsg({ id: o.id, text: `Order moved to ${to.split('_').join(' ').toLowerCase()}.` })
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update the order.')
    } finally { setBusyId(null) }
  }

  if (!orders) return <div className="container" style={{ padding: 40 }}><KSkeleton h={160} /></div>

  return (
    <div className="container" style={{ padding: '24px 20px 80px', maxWidth: 760 }}>
      <div className="k-stack">
        <h2 style={{ fontSize: 22 }}>Your orders</h2>
        {error && <KError message={error} />}

        {orders.length === 0 && (
          <KEmpty icon="🧵" title="No orders yet"
            hint="When you buy directly from an artisan, your orders and their journey appear here."
            action={<Link to="/explore" className="k-btn">Explore products</Link>} />
        )}

        {orders.length > 0 && msg && (
          <div className="k-ok" role="status">{msg.text}</div>
        )}

        <div className="k-stack">
          {orders.map((o) => {
            const done = o.status === 'DELIVERED' || o.status === 'COMPLETED'
            const nextStep: Record<string, string> = {
              CONFIRMED: 'Begin processing', PROCESSING: 'Start production',
              IN_PRODUCTION: 'Mark ready to ship', READY_TO_SHIP: 'Mark shipped', SHIPPED: 'Mark delivered',
            }
            return (
              <KCard key={o.id}>
                <div className="k-spread">
                  <div>
                    <div className="k-row">
                      <strong>{o.order_number}</strong>
                      <KBadge tone={done ? 'green' : o.status === 'CANCELLED' ? 'red' : 'blue'}>{o.status_label}</KBadge>
                      {o.is_bulk && <KBadge tone="gold">bulk</KBadge>}
                    </div>
                    <div className="muted small" style={{ marginTop: 4 }}>
                      {o.items.map((i) => `${i.title} × ${i.quantity}`).join(' · ')}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <strong className="k-price">{inr(o.total)}</strong>
                    <div className="muted small">{new Date(o.created_at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</div>
                  </div>
                </div>

                <div className="k-row" style={{ marginTop: 12 }}>
                  {nextStep[o.status] && (
                    <KButton size="sm" variant="ghost" onClick={() => void advance(o)} disabled={busyId === o.id}>
                      {nextStep[o.status]} →
                    </KButton>
                  )}
                  {(o.status === 'CONFIRMED' || o.status === 'PROCESSING') && (
                    <KButton size="sm" variant="danger" onClick={() => void advanceCancel(o.id)} disabled={busyId === o.id}>Cancel</KButton>
                  )}
                  <Link to={`/orders/${o.id}`} className="k-btn sm ghost">Details</Link>
                  {done && (
                    <KButton size="sm" variant="gold" onClick={() => void reorder(o.id)} disabled={busyId === o.id}>🔁 Buy again</KButton>
                  )}
                </div>
              </KCard>
            )
          })}
        </div>
      </div>
    </div>
  )

  async function advanceCancel(id: string) {
    setBusyId(id); setMsg(null); setError('')
    try {
      await api.post(`/orders/${id}/status`, { status: 'CANCELLED' })
      setMsg({ id, text: 'Order cancelled.' })
      load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not cancel the order.')
    } finally { setBusyId(null) }
  }
}
