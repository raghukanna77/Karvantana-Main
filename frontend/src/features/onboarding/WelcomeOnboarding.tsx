/** First-launch onboarding: language → role → name. SEE → HEAR → SPEAK first;
 *  no email/password forms, no paperwork. Authentication happens later where
 *  actually required (checkout etc.). */
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { languageInfo, type Lang } from '../../i18n/languages'
import { useT } from '../../i18n'
import { useAuth, useUi } from '../../state/stores'
import { speak } from '../../voice/voice'

const REGIONS: { name: string; codes: Lang[] }[] = [
  { name: 'All India', codes: ['hi', 'en'] },
  { name: 'South India', codes: ['ta', 'te', 'kn', 'ml'] },
  { name: 'West India', codes: ['mr', 'gu', 'kok', 'bhb'] },
  { name: 'East India', codes: ['bn', 'or', 'mai', 'sat'] },
  { name: 'North India', codes: ['pa', 'ur', 'ks'] },
  { name: 'Himalayan', codes: ['ne', 'gar', 'kfy'] },
  { name: 'North-East', codes: ['as', 'mni', 'brx'] },
  { name: 'Central India', codes: ['gon'] },
]

export default function WelcomeOnboarding() {
  const navigate = useNavigate()
  const { t } = useT()
  const lang = useUi((s) => s.lang)
  const setLang = useUi((s) => s.setLang)
  const user = useAuth((s) => s.user)
  const [step, setStep] = useState<1 | 2>(1)
  const [region, setRegion] = useState<string>(() => {
    const info = languageInfo(lang)
    return info.region
  })

  const shown = useMemo(() => {
    const codes = REGIONS.find((r) => r.name === region)?.codes ?? ['hi', 'en']
    return codes.map((c) => languageInfo(c)).filter(Boolean)
  }, [region])

  const pick = (code: Lang) => {
    setLang(code)
    speak(t('ob.done'), code)
    setStep(2)
  }

  const listen = (code: Lang) => {
    const info = languageInfo(code)
    // "Listen" speaks the language's own name in that language — audio identification.
    speak(info.nativeName, code)
  }

  const roles = [
    { icon: '👨‍🎨', key: 'ARTISAN', label: t('ob.role_artisan'), to: '/login' },
    { icon: '🛍️', key: 'BUYER', label: t('ob.role_buyer'), to: '/login' },
    { icon: '🤝', key: 'GROUP', label: t('ob.role_group'), to: '/login' },
    { icon: '🏪', key: 'B2B', label: t('ob.role_b2b'), to: '/login' },
  ]

  return (
    <div className="k-stack" style={{ maxWidth: 720, margin: '0 auto', padding: '16px 0 40px' }}>
      <div style={{ textAlign: 'center' }}>
        <div style={{ fontSize: 44 }} aria-hidden>🧵</div>
        <h1 style={{ fontSize: 26 }}>{t('ob.welcome')}</h1>
      </div>

      {step === 1 && (
        <>
          <div className="k-spread" style={{ alignItems: 'baseline', flexWrap: 'wrap' }}>
            <h2 style={{ fontSize: 20 }}>{t('ob.pick_language')}</h2>
          </div>
          <div className="k-row" style={{ flexWrap: 'wrap', gap: 8 }}>
            {REGIONS.map((r) => (
              <button key={r.name} className={`k-btn sm ${region === r.name ? 'primary' : 'ghost'}`} onClick={() => setRegion(r.name)}>
                {r.name}
              </button>
            ))}
          </div>
          <div className="k-lang-cards" role="listbox" aria-label={t('ob.pick_language')}>
            {shown.map((l) => (
              <div key={l.code} className={`k-lang-card ${lang === l.code ? 'selected' : ''}`}
                   role="option" aria-selected={lang === l.code} tabIndex={0}
                   onClick={() => pick(l.code)}
                   onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') pick(l.code) }}>
                <span className="native">{l.nativeName}</span>
                <span className="eng">{l.englishName}</span>
                <span className="cap">
                  {l.catalog === 'FULL' ? '✓✓' : l.catalog === 'CORE' ? '✓' : l.catalog === 'MINIMAL' ? '◐' : '○'}
                  {' '}{l.stt === 'YES' ? '🎤' : l.stt === 'FALLBACK' ? '🎤→' : '💬'}
                </span>
                <button className="listen" onClick={(e) => { e.stopPropagation(); listen(l.code) }}
                        aria-label={`${t('ob.listen')} ${l.englishName}`}>
                  🔊 {t('ob.listen')}
                </button>
              </div>
            ))}
          </div>
          <div className="muted small" style={{ textAlign: 'center' }}>
            ✓✓ full · ✓ core · ◐ regional pack · ○ fallback to English · 🎤 voice · 💬 visual only
          </div>
        </>
      )}

      {step === 2 && (
        <>
          <h2 style={{ fontSize: 20, textAlign: 'center' }}>{t('ob.pick_role')}</h2>
          <div className="k-choice-grid" style={{ gridTemplateColumns: 'repeat(2, 1fr)' }}>
            {roles.map((r) => (
              <button key={r.key} className="k-choice" onClick={() => navigate(r.to)}>
                <span className="k-choice-icon" aria-hidden>{r.icon}</span>
                <span className="k-choice-label">{r.label}</span>
              </button>
            ))}
          </div>
          {user && (
            <div style={{ textAlign: 'center' }}>
              <button className="k-btn ghost sm" onClick={() => navigate('/artisan')}>
                {user.full_name} → {t('nav.my_studio')}
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
