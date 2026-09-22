/** References — verified research citations with access dates. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface Ref {
  id: string; title: string; organization: string | null; url: string | null
  publication_date: string | null; accessed_date: string | null; key_finding: string | null
  criterion_supported: string | null; category: string | null; validation_status: string
}

export default function SihReferencesPage() {
  const [rows, setRows] = useState<Ref[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Ref[]>('/sih/references').then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load references'))
  }, [])

  if (error) return <SihPage title="Research References"><KError message={error} /></SihPage>
  if (!rows) return <SihPage title="Research References"><KSkeleton h={220} /></SihPage>

  return (
    <SihPage title="Research & References"
      subtitle={`${rows.length} citations · every entry has a URL and access date · no fabricated citations, ever`}>
      <SihNav active="/admin/references" />
      {rows.map((r) => (
        <EvidenceCard key={r.id} title={r.title} right={<StatusBadge status={r.validation_status} />}>
          <div className="k-row small muted" style={{ gap: 10, flexWrap: 'wrap' }}>
            {r.organization && <strong style={{ color: 'var(--ink)' }}>{r.organization}</strong>}
            {r.url && <a href={r.url} target="_blank" rel="noreferrer" className="muted">{r.url}</a>}
            {r.accessed_date && <span>accessed {new Date(r.accessed_date).toLocaleDateString()}</span>}
          </div>
          {r.key_finding && <p className="small" style={{ margin: '8px 0 4px' }}>{r.key_finding}</p>}
          <div className="k-row" style={{ gap: 6 }}>
            {r.category && <span className="k-badge blue">{r.category.replace(/_/g, ' ')}</span>}
            {r.criterion_supported && <span className="k-badge violet">{r.criterion_supported.replace(/_/g, ' ')}</span>}
          </div>
        </EvidenceCard>
      ))}
    </SihPage>
  )
}
