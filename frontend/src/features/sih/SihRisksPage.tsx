/** Risk Register — 18 tracked risks with mitigation status and validation pointers. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface Risk {
  id: string; risk_id: string; category: string; description: string
  probability: string; impact: string; severity: string; mitigation: string
  fallback: string | null; owner: string | null; status: string; validation: string | null
}

const SEV_TONE: Record<string, 'green' | 'gold' | 'red' | 'violet'> = {
  LOW: 'green', MEDIUM: 'gold', HIGH: 'red', CRITICAL: 'red',
}

export default function SihRisksPage() {
  const [rows, setRows] = useState<Risk[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Risk[]>('/sih/risks').then(setRows)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load risks'))
  }, [])

  if (error) return <SihPage title="Risk Register"><KError message={error} /></SihPage>
  if (!rows) return <SihPage title="Risk Register"><KSkeleton h={220} /></SihPage>

  const mitigated = rows.filter((r) => r.status === 'MITIGATED_IN_BUILD').length

  return (
    <SihPage wide title="Feasibility — Risk Register"
      subtitle={`${rows.length} tracked risks · ${mitigated} mitigations verifiable in the current build · every “planned” mitigation is labeled honestly, not passed off as done.`}>
      <SihNav active="/admin/risks" />

      <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', marginTop: 16 }}>
        {rows.map((r) => (
          <EvidenceCard key={r.id}
            title={`${r.risk_id} · ${r.category}`}
            right={<span className="k-row" style={{ gap: 6 }}>
              <KBadgeInline label={`P:${r.probability[0]}`} tone={SEV_TONE[r.probability] ?? 'gold'} />
              <KBadgeInline label={`I:${r.impact[0]}`} tone={SEV_TONE[r.impact] ?? 'gold'} />
            </span>}>
            <p style={{ margin: '0 0 8px', fontWeight: 600 }}>{r.description}</p>
            <div className="k-row" style={{ gap: 6, marginBottom: 8 }}>
              <KBadgeInline label={`Severity ${r.severity}`} tone={SEV_TONE[r.severity] ?? 'gold'} />
              <StatusBadge status={r.status} />
            </div>
            <div className="small"><strong>Mitigation:</strong> {r.mitigation}</div>
            {r.fallback && <div className="small muted" style={{ marginTop: 4 }}><strong>Fallback:</strong> {r.fallback}</div>}
            {r.validation && (
              <div className="muted small" style={{ marginTop: 8, padding: '6px 10px', background: 'var(--glass)', borderRadius: 8 }}>
                <strong>Verify:</strong> {r.validation}
              </div>
            )}
          </EvidenceCard>
        ))}
      </div>
    </SihPage>
  )
}

function KBadgeInline({ label, tone }: { label: string; tone: 'green' | 'gold' | 'red' | 'violet' }) {
  const colors: Record<string, string> = {
    green: '#0e6e4a', gold: '#8a6210', red: '#a91f2c', violet: '#6b21a8',
  }
  return (
    <span style={{
      fontSize: 11, padding: '2px 8px', borderRadius: 20, color: colors[tone],
      border: `1px solid ${colors[tone]}44`, background: `${colors[tone]}14`,
    }}>{label}</span>
  )
}
