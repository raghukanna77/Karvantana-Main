/** Problem → Evidence → Feature → Outcome → Metric mapping matrix. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface Link {
  id: string; problem: string; evidence: string | null; feature: string
  expected_outcome: string | null; validation_metric: string | null
  baseline: number | null; target: number | null; observed: number | null
  unit: string | null; sample_size: number | null; evidence_source: string | null
  validation_status: string
}

export default function SihProblemLinksPage() {
  const [rows, setRows] = useState<Link[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Link[]>('/sih/problem-links').then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load mappings'))
  }, [])

  if (error) return <SihPage title="Problem → Evidence → Solution"><KError message={error} /></SihPage>
  if (!rows) return <SihPage title="Problem → Evidence → Solution"><KSkeleton h={220} /></SihPage>

  return (
    <SihPage wide title="Problem → Evidence → Solution Mapping"
      subtitle="Each problem traces to evidence, the shipped feature that addresses it, and the metric that will prove the outcome. Observed values stay empty until real measurement exists.">
      <SihNav active="/admin/problem-links" />

      {rows.map((r) => (
        <EvidenceCard key={r.id} title={r.problem} right={<StatusBadge status={r.validation_status} />}>
          <div style={{ display: 'grid', gridTemplateColumns: '140px 1fr', rowGap: 8, fontSize: 13 }}>
            <span className="muted">Evidence</span><span>{r.evidence ?? '—'}</span>
            <span className="muted">KARVANTANA feature</span><span>{r.feature}</span>
            <span className="muted">Expected outcome</span><span>{r.expected_outcome ?? '—'}</span>
            <span className="muted">Validation metric</span><span>{r.validation_metric ?? '—'}</span>
          </div>
          <div className="k-row" style={{ gap: 10, marginTop: 10, flexWrap: 'wrap' }}>
            <span className="k-badge blue">baseline: {r.baseline ?? 'not set'}</span>
            <span className="k-badge violet">target: {r.target ?? 'not set'} {r.unit ?? ''}</span>
            <span className="k-badge" style={r.observed !== null
              ? { color: '#0e6e4a', borderColor: 'rgba(47,179,124,0.4)', background: 'rgba(47,179,124,0.12)' }
              : { color: '#7a5c42' }}>
              observed: {r.observed !== null ? `${r.observed} ${r.unit ?? ''}` : 'PENDING VALIDATION'}
            </span>
            {r.sample_size !== null && <span className="muted small">n={r.sample_size}</span>}
          </div>
          {r.evidence_source && <p className="muted small" style={{ margin: '8px 0 0' }}>Source: {r.evidence_source}</p>}
        </EvidenceCard>
      ))}
    </SihPage>
  )
}
