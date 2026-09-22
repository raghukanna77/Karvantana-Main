/** Artisan profile: progressive onboarding + public profile preview. */

import { useEffect, useState } from 'react'
import { api } from '../../core/api'
import type { ArtisanInfo } from '../../core/types'
import { KBadge, KButton, KCard, KInput, KLabel, KSelect, KTextarea } from '../../design'
import { LANGUAGES } from '../../i18n'
import { useUi } from '../../state/stores'
import { useT } from '../../i18n'

const CRAFT_KEYS = ['handloom', 'bamboo', 'pottery', 'coir', 'wood', 'dhokra', 'other'] as const

export default function ArtisanProfile() {
  const { t } = useT()
  const easyMode = useUi((s) => s.easyMode)
  const setEasyMode = useUi((s) => s.setEasyMode)
  const [profile, setProfile] = useState<ArtisanInfo | null>(null)
  const [form, setForm] = useState({ display_name: '', craft_specialization: '', state: '', district: '', village: '', years_of_experience: '', craft_story: '', languages: 'en' })
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.get<ArtisanInfo>('/artisans/me').then((p) => {
      setProfile(p)
      setForm((f) => ({ ...f, display_name: p.display_name, craft_specialization: p.craft ?? '', craft_story: p.story ?? '' }))
    }).catch(() => setProfile(null))
  }, [])

  async function save() {
    setError(''); setSaved(false)
    try {
      await api.patch('/artisans/me', {
        display_name: form.display_name,
        craft_specialization: form.craft_specialization,
        craft_story: form.craft_story,
        state: form.state, district: form.district, village: form.village,
        years_of_experience: Number(form.years_of_experience) || undefined,
        languages: form.languages.split(','),
      })
      setSaved(true)
      const p = await api.get<ArtisanInfo>('/artisans/me')
      setProfile(p)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Could not save.')
    }
  }

  return (
    <div className="k-stack">
      <h2 style={{ fontSize: 22 }}>🧑‍🏭 {t('profile.title')}</h2>

      {profile && (
        <KCard>
          <div className="k-spread">
            <div>
              <strong>{profile.display_name}</strong>
              <div className="muted small">{profile.craft} · {profile.location}</div>
            </div>
            <KBadge tone={profile.verification_level === 'BASIC_PROFILE' ? undefined : 'green'}>{profile.verification_level}</KBadge>
          </div>
          <hr className="k-divider" />
          <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(110px, 1fr))' }}>
            <div className="k-stat"><span className="v">{profile.stats.rating ? `${profile.stats.rating}★` : '—'}</span><span className="l">{t('profile.rating')} ({profile.stats.rating_count})</span></div>
            <div className="k-stat"><span className="v">{profile.stats.verified_orders}</span><span className="l">{t('profile.verified_orders')}</span></div>
            <div className="k-stat"><span className="v">{profile.stats.repeat_buyers}</span><span className="l">{t('profile.repeat_buyers')}</span></div>
            <div className="k-stat"><span className="v">{profile.stats.published_products}</span><span className="l">{t('nav.products')}</span></div>
          </div>
        </KCard>
      )}

      <KCard className="pad-lg">
        <h3>{t('em.toggle')}</h3>
        <div className="k-spread" style={{ alignItems: 'center' }}>
          <div>
            <div>{t('easy.title')}</div>
            <div className="muted small">{t('easy.subtitle')}</div>
          </div>
          <KButton variant={easyMode ? 'gold' : 'ghost'} size="lg" onClick={() => setEasyMode(!easyMode)}>
            {easyMode ? `✓ ${t('easy.on')}` : t('easy.off')}
          </KButton>
        </div>
      </KCard>

      <KCard className="pad-lg">
        <h3>{t('profile.business_details')}</h3>
        <KLabel>{t('profile.studio_name')}</KLabel>
        <KInput value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} placeholder="e.g. Priya's Handloom Studio" />
        <KLabel>{t('profile.craft')}</KLabel>
        <KSelect value={form.craft_specialization} onChange={(e) => setForm({ ...form, craft_specialization: e.target.value })}>
          <option value="">{t('profile.choose')}</option>
          {CRAFT_KEYS.map((k) => <option key={k} value={t(`craft.${k}`)}>{t(`craft.${k}`)}</option>)}
        </KSelect>
        <div className="k-row">
          <div style={{ flex: 1, minWidth: 130 }}>
            <KLabel>{t('profile.state')}</KLabel>
            <KInput value={form.state} onChange={(e) => setForm({ ...form, state: e.target.value })} placeholder="Tamil Nadu" />
          </div>
          <div style={{ flex: 1, minWidth: 130 }}>
            <KLabel>{t('profile.district')}</KLabel>
            <KInput value={form.district} onChange={(e) => setForm({ ...form, district: e.target.value })} />
          </div>
          <div style={{ flex: 1, minWidth: 130 }}>
            <KLabel>{t('profile.village')}</KLabel>
            <KInput value={form.village} onChange={(e) => setForm({ ...form, village: e.target.value })} />
          </div>
        </div>
        <div className="k-row">
          <div style={{ flex: 1, minWidth: 130 }}>
            <KLabel>{t('profile.experience')}</KLabel>
            <KInput value={form.years_of_experience} onChange={(e) => setForm({ ...form, years_of_experience: e.target.value })} inputMode="numeric" />
          </div>
          <div style={{ flex: 1, minWidth: 130 }}>
            <KLabel>{t('profile.languages_spoken')}</KLabel>
            <KSelect value={form.languages} onChange={(e) => setForm({ ...form, languages: e.target.value })}>
              {LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.nativeName}</option>)}
            </KSelect>
          </div>
        </div>
        <KLabel>{t('profile.story')}</KLabel>
        <KTextarea value={form.craft_story} onChange={(e) => setForm({ ...form, craft_story: e.target.value })}
                   placeholder={t('profile.story_ph')} />
        {error && <div className="k-error" style={{ marginTop: 10 }}>{error}</div>}
        {saved && <div className="k-ok" style={{ marginTop: 10 }}>{t('profile.saved')}</div>}
        <div style={{ marginTop: 14 }}>
          <KButton onClick={save} disabled={!form.display_name}>{t('profile.save')}</KButton>
        </div>
      </KCard>
    </div>
  )
}
