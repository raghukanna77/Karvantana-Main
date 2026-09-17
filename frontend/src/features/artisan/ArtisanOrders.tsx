/** Artisan order fulfilment — simple human labels, one legal next step at a time. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { inr, type OrderView } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty } from '../../design'

const NEXT_STEPS: Record<string, { to: string; label: string }[]> = {
  CONFIRMED: [{ to: 'IN_PRODUCTION', label: 'Start crafting' }, { to: 'PROCESSING', label: 'Preparing' }],
  PROCESSING: [{ to: 'IN_PRODUCTION', label: 'Craft it' }, { to: 'READY_TO_SHIP', label: 'Ready to ship' }],
  IN_PRODUCTION: [{ to: 'READY_TO_SHIP', label: 'Mark ready to ship' }],
  READY_TO_SHIP: [{ to: 'SHIPPED', label: 'Mark shipped' }],
  SHIPPED: [{ to: 'DELIVERED', label: 'Mark delivered' }],
  DELIVERED: [{ to: 'COMPLETED', label: 'Complete order' }],
}

interface BulkOpportunity {
  id: string
  title: string
  quantity: number
  max_unit_price: number | null
}

export default function ArtisanOrders() {
  const [orders, setOrders] = useState<OrderView[] | null>(null)
  const [openBulk, setOpenBulk] = useState<BulkOpportunity[]>([])
  const [error, setError] = useState('')

  async function load() {
    const [o, b] = await Promise.all([
      api.get<{ items: OrderView[] }>('/orders/artisan'),
      api.get<{ items: BulkOpportunity[] }>('/bulk-requests/open'),
    ])
    setOrders(o.items)
    setOpenBulk(b.items)
  }
  useEffect(() => { void load().catch((e) => setError(e instanceof Error ? e.message : 'Load failed')) }, [])

  async function move(order: OrderView, to: string) {
    setError('')
    try {
      await api.post(`/orders/${order.id}/status`, { status: to })
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update the order.')
    }
  }

  return (
    <div className="k-stack">
      <h2 style={{ fontSize: 22 }}>📦 Orders</h2>
      {error && <div className="k-error">{error}</div>}

      {openBulk.length > 0 && (
        <KCard>
          <div className="k-spread"><h3>🔥 Bulk opportunities</h3><KBadge tone="gold">B2B</KBadge></div>
          <p className="muted small">Open requirements from business buyers — quote from your products page.</p>
          {openBulk.map((b) => (
            <div key={b.id} className="k-spread" style={{ borderTop: '1px dashed var(--stroke)', paddingTop: 8, marginTop: 8 }}>
              <span>{b.title}</span>
              <span className="muted small">{b.quantity} units {b.max_unit_price ? `· up to ${inr(b.max_unit_price)}/unit` : ''}</span>
            </div>
          ))}
        </KCard>
      )}

      {!orders && <KCard><div className="k-skeleton" style={{ height: 140 }} /></KCard>}
      {orders && orders.length === 0 && (
        <KCard><KEmpty icon="📦" title="No orders yet" hint="Publish products and buyers will find you." /></KCard>
      )}

      {orders && orders.map((o) => {
        const steps = NEXT_STEPS[o.status] ?? []
        return (
          <KCard key={o.id}>
            <div className="k-spread">
              <strong>{o.order_number}</strong>
              <KBadge tone={o.status === 'COMPLETED' ? 'green' : o.status === 'CANCELLED' ? 'red' : 'blue'}>{o.status_label}</KBadge>
            </div>
            {o.items.map((i) => (
              <div key={i.id} className="k-row" style={{ marginTop: 8 }}>
                {i.image_url && <img src={i.image_url} alt="" style={{ width: 52, height: 52, borderRadius: 10, objectFit: 'cover' }} />}
                <div style={{ flex: 1 }}>
                  <div>{i.title}</div>
                  <div className="muted small">× {i.quantity} · {inr(i.line_total)}</div>
                </div>
              </div>
            ))}
            <div className="k-spread" style={{ marginTop: 10 }}>
              <span className="muted small">Buyer pays {inr(o.total)} (incl. platform fee {inr(o.platform_fee)})</span>
              <div className="k-row">
                {steps.map((s) => (
                  <KButton key={s.to} size="sm" onClick={() => void move(o, s.to)}>{s.label}</KButton>
                ))}
              </div>
            </div>
          </KCard>
        )
      })}
    </div>
  )
}
