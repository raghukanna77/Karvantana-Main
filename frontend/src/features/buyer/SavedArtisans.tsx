/** Saved artisans — the relationship layer: follow, revisit, reorder. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import type { ArtisanInfo } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton } from '../../design'

export default function SavedArtisansPage() {
  const [items, setItems] = useState<ArtisanInfo[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ items: ArtisanInfo[] }>('/artisans/saved/list')
      .then((r) => setItems(r.items))
      .catch((e) => setError(e instanceof Error ? e.message : 'Could not load saved artisans.'))
  }, [])

  async function unfollow(id: string) {
    try {
      await api.delete(`/artisans/${id}/follow`)
      setItems((prev) => prev?.filter((a) => a.id !== id) ?? null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not remove.')
    }
  }

  if (!items) return <div className="container" style={{ padding: 40 }}><KSkeleton h={160} /></div>

  return (
    <div className="container" style={{ padding: '24px 20px 80px', maxWidth: 760 }}>
      <div className="k-stack">
        <h2 style={{ fontSize: 22 }}>Saved artisans</h2>
        {error && <KError message={error} />}

        {items.length === 0 && (
          <KEmpty icon="🤝" title="No saved artisans yet"
            hint="After a purchase — or right from a product page — save the makers you love and come back any time."
            action={<Link to="/explore" className="k-btn">Find makers to follow</Link>} />
        )}

        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(260px, 1fr))' }}>
          {items.map((a) => (
            <KCard key={a.id}>
              <div className="k-row">
                <div style={{ width: 44, height: 44, borderRadius: '50%', background: 'linear-gradient(135deg, var(--blue), var(--violet))', display: 'grid', placeItems: 'center', fontWeight: 900 }}>
                  {a.display_name.charAt(0)}
                </div>
                <div>
                  <strong>{a.display_name}</strong>
                  <div className="muted small">{a.craft ?? 'Artisan'} · {a.location}</div>
                </div>
              </div>
              <div className="k-row" style={{ marginTop: 10 }}>
                <KBadge tone="green">{a.verification_level.replace(/_/g, ' ')}</KBadge>
                {a.stats.rating != null && <span className="muted small">{a.stats.rating}★ · {a.stats.verified_orders} orders</span>}
              </div>
              <div className="k-row" style={{ marginTop: 12 }}>
                <Link to={`/artisan-u/${a.id}`} className="k-btn sm">Visit studio</Link>
                <KButton size="sm" variant="ghost" onClick={() => void unfollow(a.id)}>Remove</KButton>
              </div>
            </KCard>
          ))}
        </div>
      </div>
    </div>
  )
}
