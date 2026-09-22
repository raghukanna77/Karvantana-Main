/** Competitor capability matrix — sourced cells only; unverified cells say NOT_EVALUATED. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KCard, KError, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface Cell {
  id: string; competitor: string; capability: string; value: string; is_karvantana: boolean
  source: string | null; verification_status: string; notes: string | null
}

const CAP_LABELS: Record<string, string> = {
  marketplace_access: 'Marketplace access', artisan_focus: 'Artisan focus',
  voice_first_cataloguing: 'Voice-first cataloguing', multilingual_ai: 'Multilingual AI',
  ai_image_assistance: 'AI image assistance', smart_pricing: 'Smart pricing',
  buyer_matching: 'Buyer matching', b2b_bulk: 'B2B / bulk', direct_reorder: 'Direct reorder',
  artisan_reputation: 'Artisan reputation', ai_business_assistant: 'AI business assistant',
  offline_first: 'Offline-first', business_intelligence: 'Business intelligence',
}

function cellStyle(value: string): React.CSSProperties {
  switch (value) {
    case 'YES': return { color: '#0e6e4a' }
    case 'PARTIAL': return { color: '#8a6210' }
    case 'NO': return { color: '#a91f2c' }
    case 'NETWORK_DEPENDENT': return { color: '#1d4ed8' }
    case 'NOT_IDENTIFIED': return { color: '#7a5c42' }
    default: return { color: '#a58a6f' } // NOT_EVALUATED — deliberately muted
  }
}

export default function SihCompetitorsPage() {
  const [cells, setCells] = useState<Cell[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<Cell[]>('/sih/competitors').then(setCells)
      .catch((e) => setError(e instanceof Error ? e.message : 'Failed to load matrix'))
  }, [])

  if (error) return <SihPage title="Competitive Landscape"><KError message={error} /></SihPage>
  if (!cells) return <SihPage title="Competitive Landscape"><KSkeleton h={220} /></SihPage>

  const competitors = [...new Set(cells.map((c) => c.competitor))]
  const capabilities = [...new Set(cells.map((c) => c.capability))]
  const cellMap = new Map(cells.map((c) => [`${c.competitor}|${c.capability}`, c]))
  const sourced = cells.filter((c) => c.source).length
  const unevaluated = cells.filter((c) => c.value === 'NOT_EVALUATED').length

  return (
    <SihPage wide title="Competitive Landscape — Capability Matrix"
      subtitle="Every cell requires a source before it claims anything. Unverified capabilities are NOT_EVALUATED — we never claim a competitor lacks a feature without research to back it.">
      <SihNav active="/admin/competitors" />

      <KCard className="pad-lg" style={{ marginTop: 16 }}>
        <div className="k-row" style={{ gap: 8 }}>
          <StatusBadge status={`${sourced} sourced`} />
          <StatusBadge status={`${unevaluated} NOT_EVALUATED`} />
          <span className="muted small">
            Verification discipline: YES / NO / PARTIAL / NETWORK_DEPENDENT / NOT_IDENTIFIED / NOT_EVALUATED
          </span>
        </div>
        <div style={{ overflowX: 'auto', marginTop: 12 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, minWidth: 720 }}>
            <thead>
              <tr style={{ textAlign: 'left' }}>
                <th className="muted small" style={{ padding: '8px' }}>Capability</th>
                {competitors.map((c) => (
                  <th key={c} className="small" style={{ padding: 8, color: c === 'KARVANTANA' ? '#b34a12' : undefined }}>{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {capabilities.map((cap) => (
                <tr key={cap} style={{ borderTop: '1px solid var(--stroke)' }}>
                  <td className="small" style={{ padding: '8px' }}>{CAP_LABELS[cap] ?? cap}</td>
                  {competitors.map((comp) => {
                    const cell = cellMap.get(`${comp}|${cap}`)
                    return (
                      <td key={comp} style={{ padding: 8 }} title={cell?.source ?? cell?.notes ?? ''}>
                        <span className="small" style={cellStyle(cell?.value ?? 'NOT_EVALUATED')}>
                          {(cell?.value ?? 'NOT_EVALUATED').replace('_', ' ')}
                        </span>
                        {cell?.is_karvantana && cell.notes && (
                          <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{cell.notes}</div>
                        )}
                      </td>
                    )
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {cells.filter((c) => c.source).map((c) => (
          <p key={c.id} className="muted small" style={{ margin: '6px 0 0' }}>
            📌 {c.competitor} · {CAP_LABELS[c.capability]}: {c.source}
          </p>
        ))}
      </KCard>

      <EvidenceCard title="Why honesty here matters">
        <p className="muted small" style={{ margin: 0 }}>
          Judges can verify any cell. A wrong claim about a competitor is disqualifying; “NOT_EVALUATED”
          is always safe and always true. Cells become evaluated only through the sourced-update API
          (POST /api/v1/sih/competitors), which records the source and access date permanently.
        </p>
      </EvidenceCard>
    </SihPage>
  )
}
