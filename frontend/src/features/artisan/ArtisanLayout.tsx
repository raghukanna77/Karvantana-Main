/** Artisan shell: topbar + mobile-first bottom navigation + Add Product FAB. */

import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../state/stores'
import { useT } from '../../i18n'
import { KLangSwitcher } from '../../design'
import { VoiceGuideButton, useVoiceGuide } from '../../design/voiceGuide'

export default function ArtisanLayout() {
  useVoiceGuide()
  const user = useAuth((s) => s.user)
  const clear = useAuth((s) => s.clear)
  const navigate = useNavigate()
  const { t } = useT()

  return (
    <div>
      <header className="k-topbar">
        <div className="container k-topbar-inner">
          <Link to="/artisan" className="k-logo"><span className="k-logo-mark">க</span> KARVANTANA</Link>
          <nav className="k-nav-links">
            <KLangSwitcher />
            <button className="k-btn sm ghost" onClick={() => { clear(); navigate('/') }}>{t('nav.sign_out')}</button>
          </nav>
        </div>
      </header>

      <main className="container" style={{ paddingTop: 18 }}>
        <Outlet />
      </main>

      <VoiceGuideButton />

      <button className="k-fab" title={t('home.add_product')} aria-label={t('home.add_product')}
              onClick={() => navigate('/artisan/products/new')}>+</button>

      <nav className="k-bottomnav" aria-label="Artisan navigation">
        {[
          { to: '/artisan', icon: '🏠', label: t('nav.home'), end: true },
          { to: '/artisan/products', icon: '🧺', label: t('nav.products') },
          { to: '/artisan/orders', icon: '📦', label: t('nav.orders') },
          { to: '/artisan/customers', icon: '❤️', label: t('home.customers') },
          { to: '/artisan/profile', icon: '🧑‍🏭', label: t('nav.profile') },
        ].map((item) => (
          <NavLink key={item.to} to={item.to} end={item.end}
                   className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="icon" aria-hidden>{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="k-bottomnav-spacer" />
      {user && <span hidden>{user.id}</span>}
    </div>
  )
}
