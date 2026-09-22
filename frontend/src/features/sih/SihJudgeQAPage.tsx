/** Judge Q&A Center — prepared answers citing only implemented reality. */

import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../../core/api'
import { KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface Q { id: string; section: string; question: string; answer: string | null; feature_link: string | null; validation_status: string }

const SECTION_LABELS: Record<string, string> = {
  PROBLEM: '🧭 Problem', INNOVATION: '💡 Innovation', TECHNICAL: '⚙️ Technical',
  FEASIBILITY: '🛠 Feasibility', BUSINESS: '💼 Business', IMPACT: '📊 Impact',
}

export default function SihJudgeQAPage() {
  const [rows, setRows] = useState<Q[] | null>(null)
  const [error, setError] = useState('')
  const [open, setOpen] = useState<string | null>(null)

  useEffect(() => {
    api.get<Q[]>('/sih/judge-questions').then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load Q&A'))
  }, [])

  if (error) return <SihPage title="Judge Q&A Center"><KError message={error} /></SihPage>
  if (!rows) return <SihPage title="Judge Q&A Center"><KSkeleton h={220} /></SihPage>

  const bySection = new Map<string, Q[]>()
  for (const q of rows) bySection.set(q.section, [...(bySection.get(q.section) ?? []), q])
  const answered = rows.filter((r) => r.answer).length

  return (
    <SihPage wide title="Judge Question Center"
      subtitle={`${rows.length} prepared questions · ${answered} answered from implemented reality · answers never cite features that don't exist`}>
      <SihNav active="/admin/judge-qa" />

      <div className="k-row" style={{ gap: 10, marginTop: 14 }}>
        <a className="k-btn sm" href="/api/v1/sih/evidence-pack/export" style={{ textDecoration: 'none' }}>
          ⬇ Download evidence pack (Markdown)
        </a>
        <span className="muted small">slide-ready: claim → evidence → source → metric → status per section</span>
      </div>

      {[...bySection.entries()].map(([section, qs]) => (
        <EvidenceCard key={section} title={SECTION_LABELS[section] ?? section}
          right={<span className="muted small">{qs.filter((q) => q.answer).length}/{qs.length} answered</span>}>
          {qs.map((q) => (
            <div key={q.id} style={{ borderTop: '1px solid var(--stroke)', padding: '10px 0' }}>
              <button className="k-spread" style={{ width: '100%', background: 'none', border: 'none', color: 'var(--ink)', cursor: 'pointer', textAlign: 'left', padding: 0 }}
                onClick={() => setOpen(open === q.id ? null : q.id)}>
                <strong style={{ fontSize: 13 }}>{q.question}</strong>
                <span className="muted">{open === q.id ? '−' : '+'}</span>
              </button>
              {open === q.id && (
                <div style={{ marginTop: 8 }}>
                  {q.answer
                    ? <p className="small" style={{ margin: 0, whiteSpace: 'pre-wrap' }}>{q.answer}</p>
                    : <p className="muted small" style={{ margin: 0 }}>Answer not yet prepared — status: PENDING VALIDATION.</p>}
                  <div className="k-row small muted" style={{ gap: 10, marginTop: 6 }}>
                    <StatusBadge status={q.validation_status} />
                    {q.feature_link && <Link to={q.feature_link} className="muted">Show in app →</Link>}
                  </div>
                </div>
              )}
            </div>
          ))}
        </EvidenceCard>
      ))}
    </SihPage>
  )
}
