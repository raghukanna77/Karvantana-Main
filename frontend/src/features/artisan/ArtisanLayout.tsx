/** Artisan shell: topbar + mobile-first bottom navigation + Add Product FAB. */

import { NavLink, Outlet, Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../state/stores'

export default function ArtisanLayout() {
  const user = useAuth((s) => s.user)
  const clear = useAuth((s) => s.clear)
  const navigate = useNavigate()

  return (
    <div>
      <header className="k-topbar">
        <div className="container k-topbar-inner">
          <Link to="/artisan" className="k-logo"><span className="k-logo-mark">க</span> KARVANTANA</Link>
          <nav className="k-nav-links">
            <button className="k-btn sm ghost" onClick={() => { clear(); navigate('/') }}>Sign out</button>
          </nav>
        </div>
      </header>

      <main className="container" style={{ paddingTop: 18 }}>
        <Outlet />
      </main>

      <button className="k-fab" title="Add Product" aria-label="Add Product"
              onClick={() => navigate('/artisan/products/new')}>+</button>

      <nav className="k-bottomnav" aria-label="Artisan navigation">
        {[
          { to: '/artisan', icon: '🏠', label: 'Home', end: true },
          { to: '/artisan/products', icon: '🧺', label: 'Products' },
          { to: '/artisan/orders', icon: '📦', label: 'Orders' },
          { to: '/artisan/insights', icon: '📊', label: 'Insights' },
          { to: '/artisan/profile', icon: '🧑‍🏭', label: 'Profile' },
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
