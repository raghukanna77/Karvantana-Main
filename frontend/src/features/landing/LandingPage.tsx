/** Public landing page — From Craft to Commerce. Fully i18n. */

import { Link } from 'react-router-dom'
import { KButton, KCard } from '../../design'
import { useT } from '../../i18n'

export default function LandingPage() {
  const { t } = useT()

  const STEPS = [
    ['📷', t('landing.step1_t'), t('landing.step1_b')],
    ['✨', t('landing.step2_t'), t('landing.step2_b')],
    ['💰', t('landing.step3_t'), t('landing.step3_b')],
    ['🌐', t('landing.step4_t'), t('landing.step4_b')],
    ['🔁', t('landing.step5_t'), t('landing.step5_b')],
  ] as const

  return (
    <div>
      <section className="container k-hero">
        <div className="k-badge violet" style={{ marginBottom: 18 }}>{t('landing.badge')}</div>
        <h1 className="hero-title">
          {t('word.craft') !== 'Craft' ? (
            <span className="grad">{t('hero.line1')}<br />{t('hero.line2')}</span>
          ) : (
            <>From <span className="grad">Craft</span><br />to <span className="grad">Commerce</span></>
          )}
        </h1>
        <p className="muted" style={{ maxWidth: 640, margin: '18px auto 28px', fontSize: 17 }}>
          {t('landing.sub')}
        </p>
        <div className="k-row" style={{ justifyContent: 'center' }}>
          <Link to="/welcome"><KButton size="lg">{t('landing.cta_start')}</KButton></Link>
          <Link to="/explore"><KButton size="lg" variant="ghost">{t('landing.cta_explore')}</KButton></Link>
        </div>
      </section>

      <section className="container" style={{ padding: '30px 20px' }}>
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))' }}>
          <KCard>
            <div style={{ fontSize: 30 }}>🧵</div>
            <h3 style={{ margin: '8px 0 6px' }}>{t('landing.problem_t')}</h3>
            <p className="muted small">{t('landing.problem_b')}</p>
          </KCard>
          <KCard>
            <div style={{ fontSize: 30 }}>🤝</div>
            <h3 style={{ margin: '8px 0 6px' }}>{t('landing.notmarketplace_t')}</h3>
            <p className="muted small">{t('landing.notmarketplace_b')}</p>
          </KCard>
          <KCard>
            <div style={{ fontSize: 30 }}>📈</div>
            <h3 style={{ margin: '8px 0 6px' }}>{t('landing.business_t')}</h3>
            <p className="muted small">{t('landing.business_b')}</p>
        </KCard>
      </div>
    </section>

      <section className="container" style={{ padding: '40px 20px' }}>
        <h2 className="section-title">{t('landing.how')}</h2>
        <div className="k-stack">
          {STEPS.map(([icon, title, body], i) => (
            <div key={title} className="k-row" style={{ alignItems: 'flex-start' }}>
              <span className="step-num">{i + 1}</span>
              <div>
                <div style={{ fontWeight: 700 }}>{icon} {title}</div>
                <div className="muted small">{body}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="container" style={{ padding: '20px 20px 40px' }}>
        <div className="k-grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))' }}>
          <KCard className="pad-lg">
            <div className="k-badge blue">{t('landing.for_artisans')}</div>
            <h3 style={{ margin: '12px 0 8px' }}>{t('landing.artisan_headline')}</h3>
            <ul className="muted small" style={{ lineHeight: 2, paddingLeft: 18 }}>
              <li>{t('landing.art_li1')}</li>
              <li>{t('landing.art_li2')}</li>
              <li>{t('landing.art_li3')}</li>
              <li>{t('landing.art_li4')}</li>
            </ul>
            <Link to="/login"><KButton block style={{ marginTop: 14 }}>{t('cta.start_selling')}</KButton></Link>
          </KCard>
          <KCard className="pad-lg">
            <div className="k-badge gold">{t('landing.for_buyers')}</div>
            <h3 style={{ margin: '12px 0 8px' }}>{t('landing.buyer_headline')}</h3>
            <ul className="muted small" style={{ lineHeight: 2, paddingLeft: 18 }}>
              <li>{t('landing.buy_li1')}</li>
              <li>{t('landing.buy_li2')}</li>
              <li>{t('landing.buy_li3')}</li>
              <li>{t('landing.buy_li4')}</li>
            </ul>
            <Link to="/explore"><KButton block variant="gold" style={{ marginTop: 14 }}>{t('cta.explore_products')}</KButton></Link>
          </KCard>
        </div>
      </section>

      <footer className="container" style={{ padding: '30px 20px 60px', textAlign: 'center' }}>
        <hr className="k-divider" />
        <p className="muted small">{t('landing.footer')}</p>
      </footer>
    </div>
  )
}
