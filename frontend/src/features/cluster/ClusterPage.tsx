/** Cluster manager console — the facilitator's view of their artisan collective. */

import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../core/api'
import { inr } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton, KVStat } from '../../design'
import { useT } from '../../i18n'

interface ClusterData {
  id: string
  name: string
  region: string | null
  analytics: { artisans: number; products: number; orders: number; revenue: number; top_crafts: string[] }
  artisans: { id: string; display_name: string; craft: string | null; state: string | null; onboarding_complete: boolean }[]
}

export default function ClusterPage() {
  const navigate = useNavigate()
  const { t } = useT()
  const [cluster, setCluster] = useState<ClusterData | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('karvantana.session') ?? 'null') as { user?: { role?: string } } | null
    if (user?.user?.role !== 'CLUSTER_MANAGER' && user?.user?.role !== 'ADMIN') { navigate('/login', { replace: true }); return }
    api.get<ClusterData>('/clusters/me')
      .then(setCluster)
      .catch((e) => setError(e instanceof Error ? e.message : 'No cluster assigned yet.'))
  }, [navigate])

  return (
    <div className="container" style={{ padding: '24px 20px 60px' }}>
      <div className="k-stack">
        <div className="k-spread">
          <div>
            <h2 style={{ fontSize: 22 }}>{cluster?.name ?? t('cluster.title')}</h2>
            <div className="muted small">{cluster?.region ?? t('cluster.subtitle')}</div>
          </div>
          <KBadge tone="violet">Cluster manager</KBadge>
        </div>
        {error && <KError message={error} />}

        {!cluster && !error && <KSkeleton h={180} />}
        {error && !cluster && (
          <KEmpty icon="🧩" title={t('cluster.none_title')}
                  hint={t('cluster.none_hint')}
                  action={<KButton variant="ghost" onClick={() => navigate('/')}>{t('cluster.back_home')}</KButton>} />
        )}

        {cluster && (
          <>
            <KCard>
              <div className="k-row" style={{ gap: 32, flexWrap: 'wrap' }}>
                <KVStat value={cluster.analytics.artisans} label="artisans" />
                <KVStat value={cluster.analytics.products} label="products" />
                <KVStat value={cluster.analytics.orders} label="orders" />
                <KVStat value={inr(cluster.analytics.revenue)} label="revenue" />
              </div>
              {cluster.analytics.top_crafts.length > 0 && (
                <>
                  <hr className="k-divider" />
                  <div className="k-row">
                    <span className="muted small">Top crafts:</span>
                    {cluster.analytics.top_crafts.map((c) => <KBadge key={c} tone="gold">{c}</KBadge>)}
                  </div>
                </>
              )}
            </KCard>

            <h3 style={{ margin: 0 }}>{t('cluster.members')} ({cluster.artisans.length})</h3>
            {cluster.artisans.length === 0 && (
              <KEmpty icon="🧑‍🤝‍🧑" title={t('cluster.no_artisans')}
                      hint={t('cluster.no_artisans_hint')} />
            )}
            <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))' }}>
              {cluster.artisans.map((a) => (
                <KCard key={a.id}>
                  <div className="k-spread">
                    <div>
                      <Link to={`/artisan-u/${a.id}`} style={{ fontWeight: 700 }}>{a.display_name}</Link>
                      <div className="muted small">{a.craft ?? 'Artisan'} · {a.state ?? ''}</div>
                    </div>
                    <KBadge tone={a.onboarding_complete ? 'green' : 'gold'}>
                      {a.onboarding_complete ? 'active' : 'onboarding'}
                    </KBadge>
                  </div>
                </KCard>
              ))}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
