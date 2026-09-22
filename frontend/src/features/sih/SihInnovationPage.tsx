/** Innovation — statement, differentiation, workflow, prior art, tech scouting. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KBadge, KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface InnovationDoc { id: string; section: string; title: string; body: string | null; workflow: { stages?: string[]; note?: string } | null; validation_status: string }
interface PriorArt { id: string; title: string; source: string; url: string | null; date_accessed: string | null; technology: string | null; relevance: string | null; similarity: string | null; differentiation: string | null }
interface TechRow {
  id: string; technology: string; layer: string; why: string; alternatives: string | null
  ai_input: string | null; ai_processing: string | null; ai_model: string | null
  ai_output: string | null; ai_validation: string | null; ai_human_override: string | null
  in_current_build: boolean
}

const LAYER_TONE: Record<string, 'blue' | 'violet' | 'green' | 'gold'> = {
  FRONTEND: 'blue', BACKEND: 'violet', DATA: 'green', AI: 'gold', INFRA: 'blue', OFFLINE: 'violet',
}

export default function SihInnovationPage() {
  const [docs, setDocs] = useState<InnovationDoc[] | null>(null)
  const [prior, setPrior] = useState<PriorArt[] | null>(null)
  const [tech, setTech] = useState<TechRow[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([
      api.get<InnovationDoc[]>('/sih/innovation'),
      api.get<PriorArt[]>('/sih/prior-art'),
      api.get<TechRow[]>('/sih/tech-scouting'),
    ]).then(([d, p, t]) => { setDocs(d); setPrior(p); setTech(t) })
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load innovation evidence'))
  }, [])

  if (error) return <SihPage title="Innovation"><KError message={error} /></SihPage>
  if (!docs || !prior || !tech) return <SihPage title="Innovation"><KSkeleton h={220} /></SihPage>


  return (
    <SihPage wide title="Innovation Evidence"
      subtitle="Statement, differentiation, traceability, prior-art log and technology scouting — every AI component documented from input to human override.">
      <SihNav active="/admin/innovation" />

      {docs.map((d) => (
        <EvidenceCard key={d.id} title={d.title} right={<StatusBadge status={d.validation_status} />}>
          {d.body && <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{d.body}</p>}
          {d.workflow?.stages && (
            <div className="k-row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 12 }}>
              {d.workflow.stages.map((s, i) => (
                <span key={s} className="k-row small" style={{ gap: 6 }}>
                  {i > 0 && <span className="muted">→</span>}
                  <span className="k-badge violet">{s}</span>
                </span>
              ))}
            </div>
          )}
          {d.workflow?.note && <p className="muted small" style={{ marginTop: 8 }}>{d.workflow.note}</p>}
        </EvidenceCard>
      ))}

      <EvidenceCard title={`Prior-art / patent search log (${prior.length} records)`}
        right={<StatusBadge status="PENDING_VALIDATION" />}>
        <p className="muted small" style={{ marginTop: 0 }}>
          Methodology: performed searches are logged with source and access date. The system never claims
          “no patent exists” — breadth of search is itself tracked as pending work.
        </p>
        {prior.map((p) => (
          <div key={p.id} style={{ borderTop: '1px solid var(--stroke)', padding: '10px 0' }}>
            <div className="k-spread">
              <strong style={{ fontSize: 13 }}>{p.title}</strong>
              <span className="muted small">{p.date_accessed ? new Date(p.date_accessed).toLocaleDateString() : ''}</span>
            </div>
            <div className="muted small">{p.source}{p.url && <> · <a href={p.url} target="_blank" rel="noreferrer" className="muted">link</a></>}</div>
            {p.relevance && <div className="small" style={{ marginTop: 4 }}>{p.relevance}</div>}
            {p.differentiation && <div className="muted small" style={{ marginTop: 2 }}>Differentiation: {p.differentiation}</div>}
          </div>
        ))}
      </EvidenceCard>

      <EvidenceCard title={`Technology scouting (${tech.length} decisions)`}
        right={<span className="muted small">{tech.filter((t) => !t.in_current_build).length} planned · {tech.filter((t) => t.in_current_build).length} shipped</span>}>
        {tech.map((t) => (
          <div key={t.id} style={{ borderTop: '1px solid var(--stroke)', padding: '12px 0' }}>
            <div className="k-spread">
              <span className="k-row" style={{ gap: 8 }}>
                <KBadge tone={LAYER_TONE[t.layer] ?? 'blue'}>{t.layer}</KBadge>
                <strong style={{ fontSize: 13 }}>{t.technology}</strong>
              </span>
              {t.in_current_build
                ? <KBadge tone="green">SHIPPED</KBadge>
                : <KBadge tone="gold">PLANNED</KBadge>}
            </div>
            <p className="small" style={{ margin: '6px 0 2px' }}>{t.why}</p>
            {t.alternatives && <p className="muted small" style={{ margin: 0 }}>Alternatives weighed: {t.alternatives}</p>}
            {t.ai_model && (
              <div className="muted small" style={{ marginTop: 8, padding: '8px 10px', background: 'var(--glass)', borderRadius: 8 }}>
                <div><strong>INPUT</strong> → {t.ai_input}</div>
                <div><strong>PROCESSING</strong> → {t.ai_processing}</div>
                <div><strong>MODEL</strong> → {t.ai_model}</div>
                <div><strong>OUTPUT</strong> → {t.ai_output}</div>
                <div><strong>VALIDATION</strong> → {t.ai_validation}</div>
                <div><strong>HUMAN OVERRIDE</strong> → {t.ai_human_override}</div>
              </div>
            )}
          </div>
        ))}
      </EvidenceCard>
    </SihPage>
  )
}
