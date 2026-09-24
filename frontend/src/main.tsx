/** KARVANTANA web app entry — routing with role guards for every surface.
 *  /artisan/* is the artisan's own workspace (mobile-first, own chrome);
 *  /artisan-u/:id is the public studio page for any artisan. */

import { StrictMode, useEffect } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useLocation, useNavigate } from 'react-router-dom'
import './styles/theme.css'
import { RequireAuth } from './routing'
import { catalogNote, useT } from './i18n'
import { languageInfo } from './i18n/languages'
import { KLangSwitcher } from './design'
import { VoiceGuideButton, useVoiceGuide } from './design/voiceGuide'
import { bgForPath } from './design/backgrounds'
import { useAuth, useUi } from './state/stores'
import LandingPage from './features/landing/LandingPage'
import WelcomeOnboarding from './features/onboarding/WelcomeOnboarding'
import AuthPage from './features/auth/AuthPage'
import ExplorePage from './features/marketplace/ExplorePage'
import ProductPage from './features/marketplace/ProductPage'
import ArtisanStudioPage from './features/artisan/ArtisanStudioHome'
import ArtisanLayout from './features/artisan/ArtisanLayout'
import ArtisanHome from './features/artisan/ArtisanHome'
import ArtisanProducts from './features/artisan/ArtisanProducts'
import ProductWizard from './features/artisan/ProductWizard'
import ArtisanOrders from './features/artisan/ArtisanOrders'
import ArtisanCustomers from './features/artisan/ArtisanCustomers'
import ArtisanInsights from './features/artisan/ArtisanInsights'
import ArtisanProfile from './features/artisan/ArtisanProfile'
import AssistantPage from './features/assistant/AssistantPage'
import WhatsAppSimulator from './features/whatsapp/WhatsAppSimulator'
import CheckoutPage from './features/buyer/CheckoutPage'
import BuyerOrders from './features/buyer/BuyerOrders'
import SavedArtisansPage from './features/buyer/SavedArtisans'
import OrderDetailPage from './features/buyer/OrderDetail'
import B2BPortalPage from './features/b2b/B2BPortalPage'
import NotificationsPage from './features/notifications/NotificationsPage'
import AdminPage from './features/admin/AdminPage'
import ClusterPage from './features/cluster/ClusterPage'
import SihReadinessPage from './features/sih/SihReadinessPage'
import SihResearchPage from './features/sih/SihResearchPage'
import SihImpactPage from './features/sih/SihImpactPage'
import SihInnovationPage from './features/sih/SihInnovationPage'
import SihRisksPage from './features/sih/SihRisksPage'
import SihCompetitorsPage from './features/sih/SihCompetitorsPage'
import SihProblemLinksPage from './features/sih/SihProblemLinksPage'
import SihJudgeQAPage from './features/sih/SihJudgeQAPage'
import SihReferencesPage from './features/sih/SihReferencesPage'
import DemoModePage from './features/sih/DemoModePage'

useAuth.getState().hydrate()

/** App-root effects: RTL direction, Easy Mode class, language document title. */
function UiRootEffects() {
  const lang = useUi((s) => s.lang)
  const easyMode = useUi((s) => s.easyMode)
  const pathname = useLocation().pathname

  // Field-related craft photo behind the UI (soft ivory veil keeps text readable).
  const bg = bgForPath(pathname)
  useEffect(() => {
    let el = document.getElementById('k-pagebg') as HTMLDivElement | null
    if (!el) {
      el = document.createElement('div')
      el.id = 'k-pagebg'
      el.className = 'k-pagebg'
      el.setAttribute('aria-hidden', 'true')
      document.body.prepend(el)
    }
    if (bg) {
      el.style.backgroundImage = `url("${bg.url}")`
      el.style.backgroundPosition = bg.align ?? 'center'
      el.style.display = 'block'
    } else {
      el.style.display = 'none'
    }
  }, [bg])

  useEffect(() => {
    const info = languageInfo(lang)
    document.documentElement.dir = info.rtl ? 'rtl' : 'ltr'
    document.documentElement.lang = lang
  }, [lang])
  useEffect(() => {
    document.documentElement.classList.toggle('k-easy', easyMode)
  }, [easyMode])
  return null
}

function TopBar() {
  const user = useAuth((s) => s.user)
  const clear = useAuth((s) => s.clear)
  const navigate = useNavigate()
  const { t } = useT()
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? 'k-nav-link active' : 'k-nav-link')
  return (
    <header className="k-topbar">
      <div className="container k-topbar-inner">
        <Link to="/" className="k-logo"><span className="k-logo-mark">க</span> KARVANTANA</Link>
        <nav className="k-nav-links">
          <NavLink to="/explore" className={cls}>{t('nav.explore')}</NavLink>
          {user && <NavLink to="/notifications" className={cls} aria-label={t('nav.notifications')}>🔔</NavLink>}
          {!user && <Link to="/login" className="k-btn sm ghost">{t('nav.sign_in')}</Link>}
          {user && (
            <>
              {user.role === 'ARTISAN' && <NavLink to="/artisan" className={cls}>{t('nav.my_studio')}</NavLink>}
              {user.role === 'B2B_BUYER' && <NavLink to="/b2b" className={cls}>{t('nav.procurement')}</NavLink>}
              {(user.role === 'BUYER') && <NavLink to="/buyer/orders" className={cls}>{t('nav.orders')}</NavLink>}
              {user.role === 'ADMIN' && <NavLink to="/admin" className={cls}>{t('nav.console')}</NavLink>}
              {(user.role === 'ADMIN' || user.role === 'CLUSTER_MANAGER') && <NavLink to="/admin/sih-readiness" className={cls}>SIH</NavLink>}
              {user.role === 'CLUSTER_MANAGER' && <NavLink to="/cluster" className={cls}>{t('nav.cluster')}</NavLink>}
              <button className="k-btn sm ghost" onClick={() => { clear(); navigate('/') }}>
                {user.full_name.split(' ')[0]} · {t('nav.sign_out')}
              </button>
            </>
          )}
          <KLangSwitcher />
        </nav>
      </div>
    </header>
  )
}

function PublicShell() {
  useVoiceGuide()
  const lang = useUi((s) => s.lang)
  const note = catalogNote(lang)
  return (
    <div>
      <TopBar />
      <VoiceGuideButton />
      {note && (
        <div className="container"><div className="muted small" style={{ padding: '6px 0' }}>{note}</div></div>
      )}
      <main><Outlet /></main>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <UiRootEffects />
      <Routes>
        {/* Public + shared (top bar chrome) */}
        <Route element={<PublicShell />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/welcome" element={<WelcomeOnboarding />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/product/:id" element={<ProductPage />} />
          <Route path="/artisan-u/:id" element={<ArtisanStudioPage />} />
          <Route path="/demo" element={<DemoModePage />} />

          <Route element={<RequireAuth roles={['BUYER', 'B2B_BUYER', 'ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/checkout/:id" element={<CheckoutPage />} />
            <Route path="/buyer/orders" element={<BuyerOrders />} />
            <Route path="/buyer/saved" element={<SavedArtisansPage />} />
          </Route>

          <Route element={<RequireAuth roles={['B2B_BUYER', 'ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/b2b" element={<B2BPortalPage />} />
          </Route>

          <Route element={<RequireAuth><Outlet /></RequireAuth>}>
            <Route path="/orders/:id" element={<OrderDetailPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
          </Route>

          <Route element={<RequireAuth roles={['ARTISAN', 'ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/assistant" element={<AssistantPage />} />
            {/* WhatsApp fallback front-end — same listing pipeline, chat transport. */}
            <Route path="/artisan/whatsapp" element={<WhatsAppSimulator />} />
          </Route>

          <Route element={<RequireAuth roles={['ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/admin" element={<AdminPage />} />
          </Route>

          <Route element={<RequireAuth roles={['ADMIN', 'CLUSTER_MANAGER']}><Outlet /></RequireAuth>}>
            <Route path="/admin/sih-readiness" element={<SihReadinessPage />} />
            <Route path="/admin/research" element={<SihResearchPage />} />
            <Route path="/admin/problem-links" element={<SihProblemLinksPage />} />
            <Route path="/admin/impact" element={<SihImpactPage />} />
            <Route path="/admin/innovation" element={<SihInnovationPage />} />
            <Route path="/admin/competitors" element={<SihCompetitorsPage />} />
            <Route path="/admin/risks" element={<SihRisksPage />} />
            <Route path="/admin/tech" element={<SihInnovationPage />} />
            <Route path="/admin/prior-art" element={<SihInnovationPage />} />
            <Route path="/admin/judge-qa" element={<SihJudgeQAPage />} />
            <Route path="/admin/references" element={<SihReferencesPage />} />
          </Route>

          <Route element={<RequireAuth roles={['CLUSTER_MANAGER', 'ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/cluster" element={<ClusterPage />} />
          </Route>
        </Route>

        {/* Artisan workspace — own mobile-first chrome */}
        <Route element={<RequireAuth roles={['ARTISAN', 'ADMIN']}><ArtisanLayout /></RequireAuth>}>
          <Route path="/artisan" element={<ArtisanHome />} />
          <Route path="/artisan/products" element={<ArtisanProducts />} />
          <Route path="/artisan/products/new" element={<ProductWizard />} />
          <Route path="/artisan/orders" element={<ArtisanOrders />} />
          <Route path="/artisan/orders/:id" element={<ArtisanOrders />} />
          <Route path="/artisan/customers" element={<ArtisanCustomers />} />
          <Route path="/artisan/insights" element={<ArtisanInsights />} />
          <Route path="/artisan/profile" element={<ArtisanProfile />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
