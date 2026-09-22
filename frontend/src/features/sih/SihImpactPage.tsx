/** Impact Metrics — real computed values from platform rows + manual definitions. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KCard, KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface MetricValue { value: number | null; sample?: number; pct?: number | null }
interface Computed {
  dataset: string; computed_at: string
  digital_enablement: Record<string, MetricValue>
  market_access: Record<string, MetricValue>
  commerce: Record<string, MetricValue>
  artisan_business: Record<string, MetricValue>
  ai_performance: Record<string, MetricValue>
}
interface ManualDef {
  id: string; category: string; code: string; name: string; direction: string; unit: string
  baseline: number | null; target: number | null; actual: number | null; provenance: string
  computed_actual: number | null; sample_size: number | null; validation_status: string
}

const LABELS: Record<string, string> = {
  artisans_onboarded: 'Artisans onboarded', products_digitized: 'Products digitized',
  products_published: 'Products published', ai_assisted_listings: 'AI-assisted listings',
  b2b_bulk_requests: 'B2B bulk requests', custom_requests: 'Custom requests',
  follows: 'Artisan follows', reviews: 'Reviews',
  orders_total: 'Orders total', orders_paid_statuses: 'Orders (paid statuses)',
  average_order_value_inr: 'Average order value (₹)', repeat_buyers: 'Repeat buyers',
  repeat_buyer_pct: 'Repeat-buyer %', artisan_buyer_repeat_order_pct: 'Buyer↔artisan repeat-order %',
  artisans_with_orders: 'Artisans with orders',
  catalogue_generations: 'Catalogue generations', ai_acceptance: 'AI fields approved',
  ai_edits: 'AI fields edited', ai_rejections: 'AI fields rejected', ai_regenerations: 'AI regenerations',
  generations_with_artisan_edits: 'Generations later edited', low_confidence_generations_lt_0_75: 'Low-confidence generations (<0.75)',
  avg_catalogue_confidence: 'Avg catalogue confidence', avg_catalogue_latency_ms: 'Avg catalogue latency (ms)',
}

function MetricRow({ k, v }: { k: string; v: MetricValue }) {
  const display = v.value === null ? '—'
    : k.endsWith('_pct') ? `${v.value}%`
    : k === 'avg_catalogue_confidence' ? v.value.toFixed(2)
    : typeof v.value === 'number' && !Number.isInteger(v.value) ? v.value.toLocaleString('en-IN') : v.value.toLocaleString('en-IN')
  return (
    <div className="k-spread" style={{ padding: '8px 0', borderBottom: '1px solid var(--stroke)' }}>
      <span className="small">{LABELS[k] ?? k}</span>
      <span className="k-row small muted" style={{ gap: 8 }}>
        {v.sample !== undefined && <span>n={v.sample}</span>}
        <strong style={{ color: 'var(--ink)' }}>{display}</strong>
      </span>
    </div>
  )
}

export default function SihImpactPage() {
  const [computed, setComputed] = useState<Computed | null>(null)
  const [manual, setManual] = useState<ManualDef[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<{ computed: Computed; manual_definitions: ManualDef[] }>('/sih/impact/computed')
      .then((d) => { setComputed(d.computed); setManual(d.manual_definitions) })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load impact metrics'))
  }, [])

  if (error) return <SihPage title="Impact Metrics"><KError message={error} /></SihPage>
  if (!computed || !manual) return <SihPage title="Impact Metrics"><KSkeleton h={220} /></SihPage>

  const sections: Array<[string, Record<string, MetricValue>]> = [
    ['DIGITAL ENABLEMENT', computed.digital_enablement],
    ['MARKET ACCESS', computed.market_access],
    ['COMMERCE', computed.commerce],
    ['ARTISAN BUSINESS', computed.artisan_business],
    ['AI PERFORMANCE', computed.ai_performance],
  ]

  return (
    <SihPage wide title="Impact Metrics"
      subtitle="Values below are computed live from platform database rows with sample sizes. The current dataset is the labeled demo dataset — real-world values arrive with pilot usage and are marked accordingly.">
      <SihNav active="/admin/impact" />

      <KCard className="pad-lg" style={{ marginTop: 16 }}>
        <div className="k-row" style={{ gap: 8 }}>
          <StatusBadge status="DEMO" />
          <span className="muted small">{computed.dataset}</span>
        </div>
        <p className="muted small" style={{ margin: '8px 0 0' }}>
          Computed {new Date(computed.computed_at).toLocaleString()} · provenance vocabulary:
          REAL (verified) · DEMO (this dataset) · TARGET (goal) · SIMULATED (model output) · PENDING_VALIDATION
        </p>
      </KCard>

      <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', marginTop: 14 }}>
        {sections.map(([title, metrics]) => (
          <EvidenceCard key={title} title={title}>
            {Object.entries(metrics).map(([k, v]) => <MetricRow key={k} k={k} v={v} />)}
          </EvidenceCard>
        ))}
      </div>

      <EvidenceCard title="Metric definitions (baselines/targets — entered only when real)"
        right={<span className="muted small">{manual.length} defined</span>}>
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr className="muted small" style={{ textAlign: 'left' }}>
                <th style={{ padding: '6px 8px' }}>Metric</th><th>Unit</th><th>Baseline</th>
                <th>Target</th><th>Actual</th><th>Provenance</th><th>Sample</th>
              </tr>
            </thead>
            <tbody>
              {manual.map((m) => (
                <tr key={m.id} style={{ borderTop: '1px solid var(--stroke)' }}>
                  <td style={{ padding: '7px 8px' }}>{m.name}</td>
                  <td className="muted small">{m.unit}</td>
                  <td>{m.baseline ?? '—'}</td>
                  <td>{m.target ?? '—'}</td>
                  <td><strong>{m.actual ?? '—'}</strong></td>
                  <td><StatusBadge status={m.provenance} /></td>
                  <td className="muted small">{m.sample_size ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="muted small" style={{ marginTop: 10 }}>
          No fabricated observations: every “Actual” cell is empty until a real value with provenance is recorded
          via the API (POST /api/v1/sih/impact/&#123;code&#125;/observation).
        </p>
      </EvidenceCard>
    </SihPage>
  )
}
