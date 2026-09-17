/** Order detail — lifecycle history, fulfilment progress, reorder. */

import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type OrderView } from '../../core/types'
import { KBadge, KButton, KCard, KError, KSkeleton } from '../../design'

const FLOW = ['PENDING_PAYMENT', 'CONFIRMED', 'PROCESSING', 'IN_PRODUCTION', 'READY_TO_SHIP', 'SHIPPED', 'DELIVERED', 'COMPLETED']

export default function OrderDetailPage() {
  const { id = '' } = useParams()
  const [o, setO] = useState<OrderView | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    api.get<OrderView>(`/orders/${id}`)
      .then(setO)
      .catch((e) => setError(e instanceof Error ? e.message : 'Order not found.'))
  }, [id])

  async function reorder() {
    if (!o) return
    setBusy(true); setError('')
    try {
      const next = await api.post<{ id: string; order_number: string }>(`/orders/${o.id}/reorder`)
      navigate(`/checkout/${next.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Reorder failed.')
    } finally { setBusy(false) }
  }

  if (error && !o) return <div className="container" style={{ padding: 40 }}><KError message={error} /></div>
  if (!o) return <div className="container" style={{ padding: 40 }}><KSkeleton h={220} /></div>

  const cancelled = o.status === 'CANCELLED' || o.status === 'REFUNDED'
  const stage = FLOW.indexOf(o.status)

  return (
    <div className="container" style={{ padding: '24px 20px 80px', maxWidth: 680 }}>
      <div className="k-stack">
        <div className="k-spread">
          <h2 style={{ fontSize: 22 }}>{o.order_number}</h2>
          <KBadge tone={cancelled ? 'red' : stage >= FLOW.indexOf('DELIVERED') ? 'green' : 'blue'}>{o.status_label}</KBadge>
        </div>
        {error && <KError message={error} />}

        {!cancelled && stage >= 0 && (
          <KCard>
            <div className="k-row" style={{ justifyContent: 'space-between' }}>
              {FLOW.slice(0, 7).map((s, i) => (
                <div key={s} style={{ textAlign: 'center', flex: 1 }}>
                  <div style={{
                    width: 22, height: 22, borderRadius: '50%', margin: '0 auto 4px',
                    background: i <= stage ? 'linear-gradient(135deg, var(--blue), var(--violet))' : 'var(--glass)',
                    border: '1px solid ' + (i <= stage ? 'transparent' : 'var(--stroke)'),
                    color: i <= stage ? '#fff' : 'transparent', fontSize: 12, display: 'grid', placeItems: 'center',
                  }}>✓</div>
                  <div className="muted" style={{ fontSize: 10, textTransform: 'capitalize' }}>{s.replace(/_/g, ' ').toLowerCase()}</div>
                </div>
              ))}
            </div>
          </KCard>
        )}

        <KCard>
          {o.items.map((i) => (
            <div key={i.id} className="k-spread" style={{ padding: '6px 0' }}>
              <span>{i.title} × {i.quantity}</span><strong>{inr(i.line_total)}</strong>
            </div>
          ))}
          <hr className="k-divider" />
          <div className="k-spread"><span className="muted small">Subtotal</span><span>{inr(o.subtotal)}</span></div>
          <div className="k-spread"><span className="muted small">Platform fee</span><span>{inr(o.platform_fee)}</span></div>
          <div className="k-spread"><strong>Total</strong><strong className="k-price">{inr(o.total)}</strong></div>
        </KCard>

        {o.history && o.history.length > 0 && (
          <KCard>
            <h3>Journey</h3>
            <div className="k-stack" style={{ marginTop: 8 }}>
              {o.history.map((h, i) => (
                <div key={i} className="k-row" style={{ justifyContent: 'space-between' }}>
                  <span className="small">{h.to.replace(/_/g, ' ').toLowerCase()}</span>
                  <span className="muted small">
                    {new Date(h.at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}
                  </span>
                </div>
              ))}
            </div>
          </KCard>
        )}

        <div className="k-row">
          {o.status === 'PENDING_PAYMENT' && (
            <Link to={`/checkout/${o.id}`} className="k-btn">Complete payment</Link>
          )}
          {(o.status === 'DELIVERED' || o.status === 'COMPLETED') && (
            <KButton variant="gold" onClick={reorder} disabled={busy}>🔁 Buy again</KButton>
          )}
          <Link to="/buyer/orders" className="k-btn ghost">All orders</Link>
        </div>
      </div>
    </div>
  )
}
