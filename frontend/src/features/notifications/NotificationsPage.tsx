/** Notification centre — real records, deep links into the relevant screen. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import type { NotificationView } from '../../core/types'
import { KBadge, KEmpty, KError, KSkeleton } from '../../design'

const ICONS: Record<string, string> = {
  ORDER_RECEIVED: '📦', PAYMENT_RECEIVED: '💳', QUOTE_RECEIVED: '🧾',
  CUSTOM_REQUEST: '✨', BULK_REQUEST: '📊', NEW_REVIEW: '⭐',
  AI_CATALOGUE_READY: '🪄', ORDER_SHIPPED: '🚚', ORDER_DELIVERED: '✅',
  ORDER_COMPLETED: '🎉', ORDER_CANCELLED: '🚫', REPEAT_CUSTOMER: '🔁',
}

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationView[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ items: NotificationView[] }>('/notifications')
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load notifications.'))
  }, [])

  async function markRead(n: NotificationView) {
    if (n.is_read) return
    try {
      await api.patch(`/notifications/${n.id}/read`, {})
      setItems((prev) => prev?.map((x) => (x.id === n.id ? { ...x, is_read: true } : x)) ?? null)
    } catch { /* non-critical */ }
  }

  if (!items) return <div className="container" style={{ padding: 40 }}><KSkeleton h={160} /></div>

  return (
    <div className="container" style={{ padding: '24px 20px 80px', maxWidth: 680 }}>
      <div className="k-stack">
        <h2 style={{ fontSize: 22 }}>Notifications</h2>
        {error && <KError message={error} />}
        {items.length === 0 && (
          <KEmpty icon="🔔" title="Nothing yet"
            hint="Orders, quotes, reviews and AI updates will land here as your business moves." />
        )}
        {items.map((n) => {
          const inner = (
            <div className="k-spread" style={{ alignItems: 'flex-start' }}>
              <div className="k-row" style={{ alignItems: 'flex-start', flexWrap: 'nowrap' }}>
                <span aria-hidden style={{ fontSize: 22 }}>{ICONS[n.type] ?? '🔔'}</span>
                <div>
                  <div className="k-row">
                    <strong style={{ fontSize: 14.5 }}>{n.title}</strong>
                    {!n.is_read && <KBadge tone="blue">new</KBadge>}
                  </div>
                  {n.body && <div className="muted small" style={{ marginTop: 2 }}>{n.body}</div>}
                  <div className="muted small" style={{ marginTop: 2, fontSize: 12 }}>
                    {new Date(n.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}
                  </div>
                </div>
              </div>
            </div>
          )
          return n.link
            ? (
              <Link key={n.id} to={n.link} className="k-card" style={{ display: 'block' }} onClick={() => void markRead(n)}>
                {inner}
              </Link>
            )
            : (
              <div key={n.id} className="k-card" onClick={() => void markRead(n)} style={{ cursor: 'pointer' }}>
                {inner}
              </div>
            )
        })}
      </div>
    </div>
  )
}
