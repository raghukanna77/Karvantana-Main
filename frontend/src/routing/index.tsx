/** Routing with role guards. Unauthenticated users are pushed to /login;
 *  role-mismatched users land on their own home, never a broken screen. */

import { Navigate, useLocation } from 'react-router-dom'
import { type ReactNode } from 'react'
import { useAuth } from '../state/stores'
import type { Role } from '../core/types'

export function RequireAuth({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const user = useAuth((s) => s.user)
  const location = useLocation()
  if (!user) return <Navigate to="/login" state={{ from: location.pathname }} replace />
  if (roles && !roles.includes(user.role)) {
    return <Navigate to={homeFor(user.role)} replace />
  }
  return <>{children}</>
}

export function homeFor(role: Role): string {
  switch (role) {
    case 'ARTISAN':
      return '/artisan'
    case 'ADMIN':
      return '/admin'
    case 'CLUSTER_MANAGER':
      return '/cluster'
    case 'B2B_BUYER':
      return '/b2b'
    default:
      return '/buyer/orders'
  }
}
