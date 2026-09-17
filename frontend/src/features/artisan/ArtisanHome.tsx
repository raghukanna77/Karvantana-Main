/** Artisan home — immediate action, real numbers only. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import { inr, type ArtisanDashboard } from '../../core/types'
import { KBadge, KCard, KEmpty, KVStat } from '../../design'
import { useAuth } from '../../state/stores'

export default function ArtisanHome() {
  const user = useAuth((s) => s.user)
  const [dash, setDash] = useState<ArtisanDashboard | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ArtisanDashboard>('/analytics/artisan/dashboard')
      .then(setDash)
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load dashboard.'))
  }, [])

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div className="k-stack">
      <div>
        <h1 style={{ fontSize: 26 }}>{greeting}, {user?.full_name?.split(' ')[0] ?? 'Artisan'}</h1>
        <div className="muted small">Today's business at a glance — all numbers come from your real orders.</div>
      </div>
      {error && <div className="k-error">{error}</div>}

      {!dash && !error && <KCard><div className="k-skeleton" style={{ height: 120 }} /></KCard>}

      {dash && (
        <>
          <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))' }}>
            <KCard><KVStat value={inr(dash.totals.month_revenue)} label="This month" /></KCard>
            <KCard><KVStat value={dash.today.new_orders} label="Orders to act on" /></KCard>
            <KCard><KVStat value={dash.today.enquiries} label="Custom enquiries" /></KCard>
            <KCard><KVStat value={`${dash.totals.repeat_rate}%`} label="Repeat buyers" /></KCard>
          </div>

          {dash.totals.orders === 0 ? (
            <KCard>
              <KEmpty icon="🧺" title="Your first order is a product away"
                      hint="Add a product — speak about it in your language and AI builds the catalogue."
                      action={<Link to="/artisan/products/new" className="k-btn primary">📷 Add Product</Link>} />
            </KCard>
          ) : (
            <KCard>
              <div className="k-spread"><h3>Top products</h3><KBadge tone="blue">by units sold</KBadge></div>
              {dash.top_products.length === 0 ? (
                <p className="muted small">No completed sales yet — your numbers appear as soon as orders are confirmed.</p>
              ) : (
                <div className="k-stack" style={{ marginTop: 10 }}>
                  {dash.top_products.map((p) => (
                    <div key={p.title} className="k-spread">
                      <span>{p.title}</span>
                      <span className="muted small">{p.units} sold · {inr(p.revenue)}</span>
                    </div>
                  ))}
                </div>
              )}
            </KCard>
          )}

          <KCard>
            <div className="k-spread"><h3>Quick actions</h3></div>
            <div className="k-row" style={{ marginTop: 10 }}>
              <Link to="/artisan/products/new" className="k-btn ghost">📷 Add Product</Link>
              <Link to="/artisan/orders" className="k-btn ghost">📦 Orders</Link>
              <Link to="/artisan/insights" className="k-btn ghost">📊 Insights</Link>
              <Link to="/artisan/assistant" className="k-btn ghost">💬 Ask KARVANTANA</Link>
            </div>
          </KCard>
        </>
      )}
    </div>
  )
}
