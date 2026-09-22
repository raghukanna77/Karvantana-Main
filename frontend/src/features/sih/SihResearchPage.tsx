/** Research & Evidence — interviews, surveys, market research (privacy by design). */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import { KBadge, KButton, KCard, KError, KInput, KLabel, KSelect, KTextarea, KSkeleton } from '../../design'
import { EvidenceCard, SihNav, SihPage, StatusBadge } from './shared'

interface ResearchRow {
  id: string; research_type: string; respondent_id: string | null; respondent_type: string | null
  craft_category: string | null; location_district: string | null; location_state: string | null
  interview_date: string | null; language: string | null; years_of_experience: number | null
  pain_points: Record<string, boolean> | null; quotes: Record<string, string> | null
  consent_status: string; key_finding: string | null; source_org: string | null
  source_url: string | null; validation_status: string; notes: string | null
}

const PAIN_LABELS: Record<string, string> = {
  pricing: 'Pricing', photography: 'Photography', catalogue: 'Catalogue', language: 'Language',
  market_access: 'Market access', repeat_orders: 'Repeat orders', digital: 'Digital literacy',
}

export default function SihResearchPage() {
  const [rows, setRows] = useState<ResearchRow[] | null>(null)
  const [error, setError] = useState('')
  const [showForm, setShowForm] = useState(false)
  const [saving, setSaving] = useState(false)
  const [form, setForm] = useState({
    research_type: 'INTERVIEW', respondent_id: '', respondent_type: 'ARTISAN',
    craft_category: '', location_district: '', location_state: '', language: 'ta',
    consent_status: 'ANONYMIZED', key_finding: '',
  })
  const [pains, setPains] = useState<Record<string, boolean>>({})

  const load = () => api.get<ResearchRow[]>('/sih/research')
    .then(setRows).catch((e) => setError(e instanceof Error ? e.message : 'Failed to load'))

  useEffect(() => { void load() }, [])

  async function save() {
    setSaving(true); setError('')
    try {
      await api.post('/sih/research', {
        ...form,
        respondent_id: form.respondent_id || undefined,
        craft_category: form.craft_category || undefined,
        location_district: form.location_district || undefined,
        location_state: form.location_state || undefined,
        pain_points: Object.fromEntries(Object.entries(pains).filter(([, v]) => v)),
        quotes: {},
      })
      setShowForm(false)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed')
    } finally { setSaving(false) }
  }

  return (
    <SihPage wide title="Research & Evidence"
      subtitle="Interviews, surveys and market research. Privacy by design: respondent codes only — names/phones are never stored; locations at district/state level.">
      <SihNav active="/admin/research" />

      <div className="k-spread" style={{ marginTop: 16 }}>
        <p className="muted small" style={{ margin: 0 }}>
          Records collected: <strong style={{ color: 'var(--ink)' }}>{rows?.length ?? '…'}</strong> ·
          consent tracked per record · every field optional except type
        </p>
        <KButton onClick={() => setShowForm(!showForm)}>{showForm ? 'Close' : '+ Record evidence'}</KButton>
      </div>

      {showForm && (
        <KCard className="pad-lg" style={{ marginTop: 14 }}>
          <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
            <div><KLabel>Type</KLabel>
              <KSelect value={form.research_type} onChange={(e) => setForm({ ...form, research_type: e.target.value })}>
                {['INTERVIEW', 'SURVEY', 'MARKET', 'GOVERNMENT', 'COMPETITOR', 'PROBLEM_VALIDATION', 'IMPACT'].map((t) =>
                  <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </KSelect>
            </div>
            <div><KLabel>Respondent type</KLabel>
              <KSelect value={form.respondent_type} onChange={(e) => setForm({ ...form, respondent_type: e.target.value })}>
                {['ARTISAN', 'WEAVER', 'MICRO_ENTREPRENEUR', 'BUYER', 'NGO', 'FACILITATOR'].map((t) =>
                  <option key={t} value={t}>{t.replace('_', ' ')}</option>)}
              </KSelect>
            </div>
            <div><KLabel>Respondent code (anonymized)</KLabel>
              <KInput value={form.respondent_id} placeholder="R-007" onChange={(e) => setForm({ ...form, respondent_id: e.target.value })} />
            </div>
            <div><KLabel>Craft category</KLabel>
              <KInput value={form.craft_category} placeholder="Handloom weaving" onChange={(e) => setForm({ ...form, craft_category: e.target.value })} />
            </div>
            <div><KLabel>District</KLabel>
              <KInput value={form.location_district} placeholder="Madurai" onChange={(e) => setForm({ ...form, location_district: e.target.value })} />
            </div>
            <div><KLabel>State</KLabel>
              <KInput value={form.location_state} placeholder="Tamil Nadu" onChange={(e) => setForm({ ...form, location_state: e.target.value })} />
            </div>
            <div><KLabel>Language</KLabel>
              <KSelect value={form.language} onChange={(e) => setForm({ ...form, language: e.target.value })}>
                {['ta', 'hi', 'te', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa', 'en'].map((l) => <option key={l}>{l}</option>)}
              </KSelect>
            </div>
            <div><KLabel>Consent</KLabel>
              <KSelect value={form.consent_status} onChange={(e) => setForm({ ...form, consent_status: e.target.value })}>
                {['ANONYMIZED', 'GRANTED', 'PENDING', 'DECLINED'].map((c) => <option key={c}>{c}</option>)}
              </KSelect>
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <KLabel>Pain points observed (tick what the respondent actually reported)</KLabel>
            <div className="k-row" style={{ gap: 6, flexWrap: 'wrap' }}>
              {Object.entries(PAIN_LABELS).map(([k, label]) => (
                <button key={k} className="k-btn sm"
                  style={{
                    background: pains[k] ? 'rgba(124,92,255,0.2)' : 'var(--glass)',
                    borderColor: pains[k] ? 'rgba(124,92,255,0.55)' : 'var(--stroke)',
                  }}
                  onClick={() => setPains({ ...pains, [k]: !pains[k] })}>
                  {pains[k] ? '✓ ' : ''}{label}
                </button>
              ))}
            </div>
          </div>
          <div style={{ marginTop: 10 }}>
            <KLabel>Key finding</KLabel>
            <KTextarea rows={3} value={form.key_finding} placeholder="What did you actually learn?"
              onChange={(e) => setForm({ ...form, key_finding: e.target.value })} />
          </div>
          {error && <KError message={error} />}
          <KButton variant="primary" style={{ marginTop: 12 }} disabled={saving} onClick={() => void save()}>
            {saving ? 'Saving…' : 'Save record'}
          </KButton>
        </KCard>
      )}

      {error && !rows && <KError message={error} />}
      {!rows && <KSkeleton h={160} />}

      {rows && rows.length === 0 && (
        <KCard className="pad-lg" style={{ marginTop: 14 }}>
          <p className="muted" style={{ margin: 0 }}>
            <strong>No research records collected yet — status: PENDING VALIDATION.</strong><br />
            This is displayed honestly everywhere the platform claims problem fit. Use “Record evidence”
            to add real interviews/surveys as they happen; the readiness checklist (Problem Fit → research)
            stays MISSING until at least one real record exists.
          </p>
        </KCard>
      )}

      {rows && rows.map((r) => (
        <EvidenceCard key={r.id}
          title={`${r.research_type.replace('_', ' ')} · ${r.respondent_id ?? 'record'}`}
          right={<StatusBadge status={r.validation_status} />}>
          <div className="k-row small muted" style={{ gap: 12, flexWrap: 'wrap' }}>
            {r.respondent_type && <span>{r.respondent_type.replace('_', ' ')}</span>}
            {r.craft_category && <span>🧵 {r.craft_category}</span>}
            {(r.location_district || r.location_state) &&
              <span>📍 {[r.location_district, r.location_state].filter(Boolean).join(', ')}</span>}
            {r.language && <span>🗣 {r.language}</span>}
            {r.years_of_experience !== null && <span>⏳ {r.years_of_experience} yrs</span>}
            <span>consent: {r.consent_status}</span>
          </div>
          {r.pain_points && (
            <div className="k-row" style={{ gap: 6, marginTop: 8, flexWrap: 'wrap' }}>
              {Object.entries(r.pain_points).filter(([, v]) => v).map(([k]) => (
                <KBadge key={k} tone="gold">{PAIN_LABELS[k] ?? k}</KBadge>
              ))}
            </div>
          )}
          {r.key_finding && <p style={{ marginBottom: 0 }}>{r.key_finding}</p>}
          {r.quotes && Object.keys(r.quotes).length > 0 && (
            <blockquote className="muted small" style={{ borderLeft: '2px solid var(--stroke)', paddingLeft: 10 }}>
              “{Object.values(r.quotes)[0]}”
            </blockquote>
          )}
        </EvidenceCard>
      ))}
    </SihPage>
  )
}

