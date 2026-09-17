/** Admin console — platform overview, moderation, AI governance, audit trail.
 *  All numbers come from real records (blueprint §67: no fabricated impact). */

import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../../core/api'
import { inr } from '../../core/types'
import { KBadge, KButton, KCard, KEmpty, KError, KSkeleton, KVStat } from '../../design'

interface Overview {
  artisans: number; active_products: number; orders: number
  gmv: number; month_gmv: number; buyers: number; repeat_rate: number
}
interface ModerationItem { id: string; title: string; artisan: string; lifecycle: string; price: number; updated_at: string }
interface AIMetrics {
  requests: number; failed: number; success_rate: number | null; avg_latency_ms: number
  low_confidence_outputs: number; human_corrections: number; estimated_cost_usd: number
  by_task: { task: string; requests: number; avg_latency_ms: number }[]
}
interface AuditItem { id: string; action: string; actor_id: string; detail: string | null; created_at: string }

type Tab = 'overview' | 'moderation' | 'ai' | 'audit'

export default function AdminPage() {
  const navigate = useNavigate()
  const [tab, setTab] = useState<Tab>('overview')
  const [ov, setOv] = useState<Overview | null>(null)
  const [queue, setQueue] = useState<ModerationItem[] | null>(null)
  const [ai, setAi] = useState<AIMetrics | null>(null)
  const [audit, setAudit] = useState<AuditItem[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const user = JSON.parse(localStorage.getItem('karvantana.session') ?? 'null') as { user?: { role?: string } } | null
    if (user?.user?.role !== 'ADMIN') { navigate('/login', { replace: true }); return }
    api.get<Overview>('/analytics/admin/overview').then(setOv).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load.'))
    api.get<{ items: ModerationItem[] }>('/admin/moderation/products').then((r) => setQueue(r.items)).catch(() => setQueue([]))
    api.get<AIMetrics>('/admin/ai/monitoring').then(setAi).catch(() => setAi(null))
    api.get<{ items: AuditItem[] }>('/admin/audit-logs').then((r) => setAudit(r.items)).catch(() => setAudit([]))
  }, [navigate])

  return (
    <div className="container" style={{ padding: '24px 20px 60px' }}>
      <div className="k-stack">
        <div className="k-spread">
          <div>
            <h2 style={{ fontSize: 22 }}>Platform console</h2>
            <div className="muted small">Every figure is computed from real platform records.</div>
          </div>
          <KBadge tone="gold">Admin</KBadge>
        </div>
        {error && <KError message={error} />}

        <div className="k-row">
          {(['overview', 'moderation', 'ai', 'audit'] as Tab[]).map((t) => (
            <KButton key={t} size="sm" variant={tab === t ? 'primary' : 'ghost'} onClick={() => setTab(t)}>
              {t === 'ai' ? 'AI governance' : t}
            </KButton>
          ))}
        </div>

        {tab === 'overview' && (
          !ov ? <KSkeleton h={180} /> : (
            <KCard>
              <div className="k-row" style={{ gap: 32, flexWrap: 'wrap' }}>
                <KVStat value={ov.artisans} label="artisans" />
                <KVStat value={ov.active_products} label="active products" />
                <KVStat value={ov.orders} label="orders" />
                <KVStat value={ov.buyers} label="buyers" />
                <KVStat value={inr(ov.gmv)} label="GMV" />
                <KVStat value={`${ov.repeat_rate}%`} label="repeat rate" />
              </div>
              <hr className="k-divider" />
              <div className="muted small">This month: {inr(ov.month_gmv)} GMV</div>
              <div className="k-row" style={{ marginTop: 12 }}>
                <Link to="/explore" className="k-btn sm ghost">View marketplace</Link>
              </div>
            </KCard>
          )
        )}

        {tab === 'moderation' && (
          queue === null ? <KSkeleton h={160} /> : queue.length === 0 ? (
            <KEmpty icon="🛡️" title="Moderation queue is clear" hint="Products submitted for review will appear here." />
          ) : (
            <div className="k-stack">
              {queue.map((p) => (
                <KCard key={p.id}>
                  <div className="k-spread">
                    <div>
                      <Link to={`/product/${p.id}`} style={{ fontWeight: 700 }}>{p.title}</Link>
                      <div className="muted small">by {p.artisan} · {inr(p.price)}</div>
                    </div>
                    <div className="k-row">
                      <KBadge tone={p.lifecycle === 'PUBLISHED' ? 'green' : 'gold'}>{p.lifecycle.replace(/_/g, ' ')}</KBadge>
                      <Link to={`/product/${p.id}`} className="k-btn sm ghost">Inspect</Link>
                    </div>
                  </div>
                </KCard>
              ))}
            </div>
          )
        )}

        {tab === 'ai' && (
          !ai ? <KSkeleton h={160} /> : (
            <div className="k-stack">
              <KCard>
                <div className="k-row" style={{ gap: 32, flexWrap: 'wrap' }}>
                  <KVStat value={ai.requests} label="AI requests" />
                  <KVStat value={ai.success_rate == null ? '—' : `${ai.success_rate}%`} label="success rate" />
                  <KVStat value={`${ai.avg_latency_ms}ms`} label="avg latency" />
                  <KVStat value={ai.failed} label="failed" />
                  <KVStat value={ai.low_confidence_outputs} label="low-confidence" />
                  <KVStat value={ai.human_corrections} label="human corrections" />
                  <KVStat value={`$${ai.estimated_cost_usd.toFixed(4)}`} label="est. cost" />
                </div>
              </KCard>
              {ai.by_task.length > 0 && (
                <KCard>
                  <h3>By task</h3>
                  <div className="k-stack" style={{ marginTop: 8 }}>
                    {ai.by_task.map((t) => (
                      <div key={t.task} className="k-spread">
                        <span>{t.task.replace(/_/g, ' ')}</span>
                        <span className="muted small">{t.requests} requests · {t.avg_latency_ms}ms avg</span>
                      </div>
                    ))}
                  </div>
                </KCard>
              )}
            </div>
          )
        )}

        {tab === 'audit' && (
          audit === null ? <KSkeleton h={160} /> : audit.length === 0 ? (
            <KEmpty icon="📜" title="No audit entries yet" hint="Important actions are recorded here automatically." />
          ) : (
            <div className="k-stack">
              {audit.map((a) => (
                <KCard key={a.id}>
                  <div className="k-spread">
                    <div>
                      <strong style={{ fontSize: 14 }}>{a.action}</strong>
                      {a.detail && <div className="muted small">{a.detail}</div>}
                    </div>
                    <span className="muted small">{new Date(a.created_at).toLocaleString('en-IN', { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}</span>
                  </div>
                </KCard>
              ))}
            </div>
          )
        )}
      </div>
    </div>
  )
}
