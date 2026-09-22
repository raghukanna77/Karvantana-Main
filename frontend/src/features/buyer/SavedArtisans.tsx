/** Saved artisans — the relationship layer: follow, revisit, reorder. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import type { ArtisanInfo } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton } from '../../design'
import { useT } from '../../i18n'

export default function SavedArtisansPage() {
  const { t } = useT()
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
        <h2 style={{ fontSize: 22 }}>{t('nav.saved')}</h2>
        {error && <KError message={error} />}

        {items.length === 0 && (
          <KEmpty icon="🤝" title={t('saved.none_title')}
            hint={t('saved.none_hint')}
            action={<Link to="/explore" className="k-btn">{t('saved.find_makers')}</Link>} />
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
                <Link to={`/artisan-u/${a.id}`} className="k-btn sm">{t('saved.visit_studio')}</Link>
                <KButton size="sm" variant="ghost" onClick={() => void unfollow(a.id)}>{t('saved.remove')}</KButton>
              </div>
            </KCard>
          ))}
        </div>
      </div>
    </div>
  )
}
