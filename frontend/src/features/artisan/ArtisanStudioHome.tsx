/** Public artisan studio — the person behind the products, with real follow. */

import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, serverUrl } from '../../core/api'
import { inr, type ArtisanInfo } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton, KVStat } from '../../design'

export default function ArtisanStudioPage() {
  const { id = '' } = useParams()
  const [a, setA] = useState<ArtisanInfo | null>(null)
  const [error, setError] = useState('')
  const [following, setFollowing] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get<ArtisanInfo>(`/artisans/${id}`)
      .then((r) => { setA(r); setFollowing(r.stats.following ?? false) })
      .catch((e) => setError(e instanceof Error ? e.message : 'Artisan not found.'))
  }, [id])

  async function toggleFollow() {
    if (!a) return
    setBusy(true); setError('')
    try {
      if (following) { await api.delete(`/artisans/${a.id}/follow`); setFollowing(false) }
      else { await api.post(`/artisans/${a.id}/follow`); setFollowing(true) }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not update follow.')
    } finally { setBusy(false) }
  }

  if (error && !a) return <div className="container" style={{ padding: 40 }}><KError message={error} /></div>
  if (!a) return <div className="container" style={{ padding: 40 }}><KSkeleton h={240} /></div>

  return (
    <div className="container" style={{ padding: '24px 20px 80px', maxWidth: 900 }}>
      <div className="k-stack">
        <KCard className="pad-lg k-weave">
          <div className="k-spread">
            <div className="k-row">
              <div style={{ width: 72, height: 72, borderRadius: '50%', background: 'linear-gradient(135deg, var(--blue), var(--violet))', display: 'grid', placeItems: 'center', fontWeight: 900, fontSize: 26 }}>
                {a.display_name.charAt(0)}
              </div>
              <div>
                <div className="k-row">
                  <h2 style={{ fontSize: 24, margin: 0 }}>{a.display_name}</h2>
                  <KBadge tone="green">{a.verification_level.replace(/_/g, ' ')}</KBadge>
                </div>
                <div className="muted">{a.craft ?? 'Artisan'} · {a.location}</div>
              </div>
            </div>
            <KButton variant={following ? 'ghost' : 'primary'} onClick={toggleFollow} disabled={busy}>
              {following ? '✓ Following' : '+ Follow'}
            </KButton>
          </div>
          {a.story && <p className="muted" style={{ marginTop: 14, maxWidth: 640 }}>{a.story}</p>}
          <div className="k-row" style={{ marginTop: 14, gap: 28 }}>
            {a.stats.rating != null && <KVStat value={`${a.stats.rating}★`} label={`${a.stats.rating_count} reviews`} />}
            <KVStat value={a.stats.verified_orders} label="verified orders" />
            <KVStat value={a.stats.repeat_buyers} label="repeat buyers" />
            <KVStat value={`${Math.round(a.stats.response_rate * 100)}%`} label="response rate" />
            <KVStat value={`${Math.round(a.stats.on_time_rate * 100)}%`} label="on-time" />
          </div>
        </KCard>

        <div className="k-row">
          <h3 style={{ margin: '6px 0 0' }}>Studio catalogue</h3>
          <span className="muted small">{a.products?.length ?? 0} pieces</span>
        </div>

        {(a.products?.length ?? 0) === 0
          ? <KEmpty icon="🧶" title="No published products yet" hint="Check back soon — new work is on the loom." />
          : (
            <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))' }}>
              {(a.products ?? []).map((p) => (
                <Link key={p.id} to={`/product/${p.id}`} className="k-product-card k-card">
                  {p.image_url
                    ? <img src={serverUrl(p.image_url)} alt={p.title} loading="lazy" className="ph" />
                    : <div style={{ aspectRatio: '1', background: 'var(--navy-700)' }} aria-hidden />}
                  <div className="body">
                    <div style={{ fontWeight: 700, fontSize: 14 }}>{p.title}</div>
                    <div className="k-row" style={{ marginTop: 6 }}>
                      <span className="k-price">{inr(p.price)}</span>
                      {p.customization_available && <span className="muted small">customizable</span>}
                    </div>
                  </div>
                </Link>
              ))}
            </div>
          )}
      </div>
    </div>
  )
}
