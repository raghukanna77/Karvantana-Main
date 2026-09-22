/** SIH Evaluation Readiness — five-criterion rollup with real evidence links. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../../core/api'
import { KError, KSkeleton } from '../../design'
import { EvidenceCard, Pct, SihNav, SihPage, StatusBadge } from './shared'

interface ChecklistItem {
  id: string; code: string; requirement: string; evidence: string | null
  missing: string | null; status: string; feature_link: string | null
  doc_link: string | null; demo_ready: boolean; weight: number
}
interface Criterion {
  criterion: string; completion_pct: number | null; total: number; complete: number
  partial: number; pending: number; missing: number; demo_ready: boolean; items: ChecklistItem[]
}
interface Readiness { criteria: Criterion[]; overall_pct: number; generated_at: string }
interface TestReport {
  available: boolean; total?: number; passed?: number; failed?: number; skipped?: number
  duration_s?: number; source?: string; note?: string
}

const CRITERION_LABEL: Record<string, string> = {
  PROBLEM_FIT: 'Problem Fit · 20%',
  INNOVATION: 'Innovation · 20%',
  FEASIBILITY: 'Feasibility · 20%',
  TECH_DEPTH: 'Tech Depth · 20%',
  PRESENTATION: 'Presentation · 20%',
}

export default function SihReadinessPage() {
  const [data, setData] = useState<Readiness | null>(null)
  const [tests, setTests] = useState<TestReport | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<Readiness>('/sih/readiness'),
      api.get<TestReport>('/sih/tests'),
    ])
      .then(([r, t]) => { setData(r); setTests(t) })
      .catch((e) => setError(e instanceof ApiError ? e.message : 'Failed to load readiness.'))
  }, [])

  if (error) return <SihPage title="SIH Evaluation Readiness"><KError message={error} /></SihPage>
  if (!data) return <SihPage title="SIH Evaluation Readiness"><KSkeleton h={240} /></SihPage>

  return (
    <SihPage wide title="KARVANTANA — SIH Evaluation Readiness"
      subtitle={`Evidence-based rubric coverage · generated ${new Date(data.generated_at).toLocaleString()} · no scores are invented — every status traces to a checklist row`}>
      <SihNav active="/admin/sih-readiness" />

      <div className="k-card pad-lg" style={{ marginTop: 18, textAlign: 'center' }}>
        <div style={{ fontSize: 42, fontWeight: 700, color: '#6b21a8' }}>
          {data.overall_pct !== null ? `${Math.round(data.overall_pct)}%` : '—'}
        </div>
        <div className="muted">evidence checklist completion · five criteria × 20%</div>
      </div>

      <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', marginTop: 16 }}>
        {data.criteria.map((c) => (
          <EvidenceCard key={c.criterion}
            title={CRITERION_LABEL[c.criterion] ?? c.criterion}
            right={<Pct value={c.completion_pct} />}>
            <div className="k-row" style={{ gap: 8, marginBottom: 10 }}>
              <StatusBadge status={`${c.complete} complete`} />
              {c.partial > 0 && <StatusBadge status={`${c.partial} partial`} />}
              {c.pending > 0 && <StatusBadge status={`${c.pending} pending`} />}
              {c.missing > 0 && <StatusBadge status={`${c.missing} missing`} />}
            </div>
            <div style={{ height: 6, background: 'var(--glass)', borderRadius: 3, overflow: 'hidden' }}>
              <div style={{ width: `${c.completion_pct ?? 0}%`, height: '100%', background: 'linear-gradient(90deg, var(--blue), var(--violet))' }} />
            </div>
            <ul style={{ margin: '12px 0 0', padding: 0, listStyle: 'none' }}>
              {c.items.map((i) => (
                <li key={i.id} style={{ padding: '10px 0', borderTop: '1px solid var(--stroke)' }}>
                  <div className="k-spread">
                    <strong style={{ fontSize: 13 }}>{i.requirement}</strong>
                    <StatusBadge status={i.status} />
                  </div>
                  {i.evidence && <div className="muted small" style={{ marginTop: 4 }}>✓ {i.evidence}</div>}
                  {i.missing && <div className="muted small" style={{ marginTop: 2, color: '#8a6210' }}>⚠ Missing: {i.missing}</div>}
                  <div className="k-row small muted" style={{ gap: 10, marginTop: 4 }}>
                    {i.feature_link && <Link to={i.feature_link} className="muted">Open feature →</Link>}
                    {i.doc_link && <span>📄 {i.doc_link}</span>}
                    {i.demo_ready && <span style={{ color: '#0e6e4a' }}>demo-ready</span>}
                  </div>
                </li>
              ))}
            </ul>
          </EvidenceCard>
        ))}
      </div>

      <EvidenceCard title="Testing — real report from the last pytest run"
        right={tests?.available ? <StatusBadge status="COMPLETE" /> : <StatusBadge status="PENDING_VALIDATION" />}>
        {tests?.available ? (
          <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))' }}>
            <div className="k-stat"><span className="v">{tests.total}</span><span className="l">Tests</span></div>
            <div className="k-stat"><span className="v" style={{ color: '#0e6e4a' }}>{tests.passed}</span><span className="l">Passed</span></div>
            <div className="k-stat"><span className="v" style={{ color: tests.failed ? '#a91f2c' : undefined }}>{tests.failed}</span><span className="l">Failed</span></div>
            <div className="k-stat"><span className="v">{tests.skipped}</span><span className="l">Skipped</span></div>
            <div className="k-stat"><span className="v">{tests.duration_s}s</span><span className="l">Duration</span></div>
          </div>
        ) : (
          <p className="muted small">{tests?.note ?? 'No test artifact yet.'}</p>
        )}
        {tests?.source && <p className="muted small" style={{ marginTop: 8 }}>Source artifact: {tests.source}</p>}
        <p className="muted small">Coverage is NOT displayed because it has not been measured — the dashboard refuses to estimate.</p>
      </EvidenceCard>
    </SihPage>
  )
}
