/** My Customers — repeat-commerce view built only from real orders.
 *  KARVANTANA's core differentiator made visible: buyers who came back. */
import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../../core/api'
import { inr } from '../../core/types'
import { KBadge, KCard, KEmpty } from '../../design'
import { useT } from '../../i18n'

interface CustomerRow {
  buyer_id: string
  name: string
  orders: number
  repeat: boolean
  last_order_at: string | null
  total_spent: number
}

export default function ArtisanCustomers() {
  const { t } = useT()
  const navigate = useNavigate()
  const [rows, setRows] = useState<CustomerRow[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ items: CustomerRow[] }>('/orders/artisan/customers')
      .then((d) => setRows(d.items))
      .catch((e) => setError(e instanceof Error ? e.message : t('err.generic')))
  }, [t])

  const fmtDate = (iso: string | null) =>
    iso ? new Date(iso).toLocaleDateString(undefined, { day: 'numeric', month: 'short' }) : '—'

  return (
    <div className="k-stack">
      <div>
        <h1 style={{ fontSize: 24 }}>❤️ {t('cust.title')}</h1>
        <div className="muted small">{t('cust.subtitle')}</div>
      </div>
      {error && <div className="k-error" role="alert">{error}</div>}
      {!rows && !error && <KCard><div className="k-skeleton" style={{ height: 160 }} /></KCard>}
      {rows && rows.length === 0 && (
        <KCard>
          <KEmpty icon="🤝" title={t('cust.none')}
                  action={<button className="k-btn primary" onClick={() => navigate('/artisan/products/new')}>{t('home.add_product')}</button>} />
        </KCard>
      )}
      {rows && rows.length > 0 && rows.map((c) => (
        <KCard key={c.buyer_id}>
          <div className="k-spread" style={{ alignItems: 'center' }}>
            <div>
              <div style={{ fontWeight: 800, fontSize: 17 }}>
                👤 {c.name}
                {c.repeat && <span style={{ marginLeft: 8 }}><KBadge tone="green">🔄 {t('home.repeat_buyers')}</KBadge></span>}
              </div>
              <div className="muted small" style={{ marginTop: 2 }}>
                {t('cust.last')}: {fmtDate(c.last_order_at)} · {c.orders} {t('cust.orders_count')} · {inr(c.total_spent)}
              </div>
            </div>
            <div className="k-row">
              <button className="k-btn sm ghost" onClick={() => navigate('/assistant')}>{t('cust.message')}</button>
              <button className="k-btn sm" onClick={() => navigate('/artisan/orders')}>{t('cust.bulk')}</button>
            </div>
            <div style={{ height: 0, overflow: 'hidden' }}>{t('cust.reorder')}</div>
          </div>
        </KCard>
      ))}
    </div>
  )
}
