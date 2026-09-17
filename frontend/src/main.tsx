/** KARVANTANA web app entry — routing with role guards for every surface.
 *  /artisan/* is the artisan's own workspace (mobile-first, own chrome);
 *  /artisan-u/:id is the public studio page for any artisan. */

import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useNavigate } from 'react-router-dom'
import './styles/theme.css'
import { RequireAuth } from './routing'
import { useAuth } from './state/stores'
import LandingPage from './features/landing/LandingPage'
import AuthPage from './features/auth/AuthPage'
import ExplorePage from './features/marketplace/ExplorePage'
import ProductPage from './features/marketplace/ProductPage'
import ArtisanStudioPage from './features/artisan/ArtisanStudioHome'
import ArtisanLayout from './features/artisan/ArtisanLayout'
import ArtisanHome from './features/artisan/ArtisanHome'
import ArtisanProducts from './features/artisan/ArtisanProducts'
import ProductWizard from './features/artisan/ProductWizard'
import ArtisanOrders from './features/artisan/ArtisanOrders'
import ArtisanInsights from './features/artisan/ArtisanInsights'
import ArtisanProfile from './features/artisan/ArtisanProfile'
import AssistantPage from './features/assistant/AssistantPage'
import CheckoutPage from './features/buyer/CheckoutPage'
import BuyerOrders from './features/buyer/BuyerOrders'
import SavedArtisansPage from './features/buyer/SavedArtisans'
import OrderDetailPage from './features/buyer/OrderDetail'
import B2BPortalPage from './features/b2b/B2BPortalPage'
import NotificationsPage from './features/notifications/NotificationsPage'
import AdminPage from './features/admin/AdminPage'
import ClusterPage from './features/cluster/ClusterPage'

useAuth.getState().hydrate()

function TopBar() {
  const user = useAuth((s) => s.user)
  const clear = useAuth((s) => s.clear)
  const navigate = useNavigate()
  const cls = ({ isActive }: { isActive: boolean }) => (isActive ? 'k-nav-link active' : 'k-nav-link')
  return (
    <header className="k-topbar">
      <div className="container k-topbar-inner">
        <Link to="/" className="k-logo"><span className="k-logo-mark">க</span> KARVANTANA</Link>
        <nav className="k-nav-links">
          <NavLink to="/explore" className={cls}>Explore</NavLink>
          {user && <NavLink to="/notifications" className={cls} aria-label="Notifications">🔔</NavLink>}
          {!user && <Link to="/login" className="k-btn sm ghost">Sign in</Link>}
          {user && (
            <>
              {user.role === 'ARTISAN' && <NavLink to="/artisan" className={cls}>My studio</NavLink>}
              {user.role === 'B2B_BUYER' && <NavLink to="/b2b" className={cls}>Procurement</NavLink>}
              {(user.role === 'BUYER') && <NavLink to="/buyer/orders" className={cls}>Orders</NavLink>}
              {user.role === 'ADMIN' && <NavLink to="/admin" className={cls}>Console</NavLink>}
              {user.role === 'CLUSTER_MANAGER' && <NavLink to="/cluster" className={cls}>Cluster</NavLink>}
              <button className="k-btn sm ghost" onClick={() => { clear(); navigate('/') }}>
                {user.full_name.split(' ')[0]} · Sign out
              </button>
            </>
          )}
        </nav>
      </div>
    </header>
  )
}

function PublicShell() {
  return (
    <div>
      <TopBar />
      <main><Outlet /></main>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <Routes>
        {/* Public + shared (top bar chrome) */}
        <Route element={<PublicShell />}>
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<AuthPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/product/:id" element={<ProductPage />} />
          <Route path="/artisan-u/:id" element={<ArtisanStudioPage />} />

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
          </Route>

          <Route element={<RequireAuth roles={['ADMIN']}><Outlet /></RequireAuth>}>
            <Route path="/admin" element={<AdminPage />} />
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
          <Route path="/artisan/insights" element={<ArtisanInsights />} />
          <Route path="/artisan/profile" element={<ArtisanProfile />} />
        </Route>

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </StrictMode>,
)
