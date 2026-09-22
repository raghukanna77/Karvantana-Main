/** SIH evidence pages — shared helpers. */

import { Link } from 'react-router-dom'
import { KBadge } from '../../design'

export type SihStatus =
  | 'COMPLETE' | 'DEMO_READY' | 'PARTIALLY_COMPLETE' | 'PENDING_VALIDATION' | 'MISSING'
  | 'NOT_EVALUATED' | 'MITIGATED_IN_BUILD' | 'MITIGATION_PLANNED' | 'OPEN'
  | 'REAL' | 'DEMO' | 'TARGET' | 'SIMULATED'

const TONE: Record<string, 'green' | 'gold' | 'violet' | 'red' | 'blue'> = {
  COMPLETE: 'green', DEMO_READY: 'green', MITIGATED_IN_BUILD: 'green',
  PARTIALLY_COMPLETE: 'gold', PENDING_VALIDATION: 'violet', MITIGATION_PLANNED: 'violet',
  MISSING: 'red', OPEN: 'red',
  NOT_EVALUATED: 'blue', REAL: 'green', DEMO: 'gold', TARGET: 'violet', SIMULATED: 'gold',
}

export function StatusBadge({ status }: { status: string }) {
  return <KBadge tone={TONE[status] ?? 'blue'}>{status.replace(/_/g, ' ')}</KBadge>
}

export function SihPage({ title, subtitle, children, wide }: {
  title: string; subtitle?: string; children: React.ReactNode; wide?: boolean
}) {
  return (
    <div className="container" style={{ maxWidth: wide ? 1180 : 860, padding: '28px 20px 80px' }}>
      <h1 style={{ fontSize: 26, marginBottom: 6 }}>{title}</h1>
      {subtitle && <p className="muted" style={{ marginTop: 0 }}>{subtitle}</p>}
      {children}
    </div>
  )
}

export function EvidenceCard({ title, right, children }: {
  title: string; right?: React.ReactNode; children: React.ReactNode
}) {
  return (
    <div className="k-card pad-lg" style={{ marginTop: 16 }}>
      <div className="k-spread" style={{ alignItems: 'baseline' }}>
        <h3 style={{ margin: '0 0 8px' }}>{title}</h3>
        {right}
      </div>
      {children}
    </div>
  )
}

export function Pct({ value }: { value: number | null }) {
  if (value === null || value === undefined) return <span className="muted">—</span>
  const tone = value >= 80 ? '#0e6e4a' : value >= 40 ? '#8a6210' : '#a91f2c'
  return <strong style={{ color: tone }}>{Math.round(value)}%</strong>
}

export function SihNav({ active }: { active: string }) {
  const items: Array<[string, string]> = [
    ['/admin/sih-readiness', 'Readiness'],
    ['/admin/research', 'Research'],
    ['/admin/problem-links', 'Problem→Evidence'],
    ['/admin/impact', 'Impact'],
    ['/admin/innovation', 'Innovation'],
    ['/admin/competitors', 'Competitors'],
    ['/admin/risks', 'Risks'],
    ['/admin/tech', 'Tech & AI'],
    ['/admin/prior-art', 'Prior Art'],
    ['/admin/judge-qa', 'Judge Q&A'],
    ['/admin/references', 'References'],
    ['/demo', 'Demo Mode'],
  ]
  return (
    <nav className="k-row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 18 }}>
      {items.map(([to, label]) => (
        <Link key={to} to={to}
          className="k-btn sm"
          style={{
            background: active === to ? 'rgba(124,92,255,0.18)' : 'var(--glass)',
            borderColor: active === to ? 'rgba(124,92,255,0.5)' : 'var(--stroke)',
            color: 'var(--ink)', textDecoration: 'none',
          }}>
          {label}
        </Link>
      ))}
    </nav>
  )
}
