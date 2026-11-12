import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router'
import { GuestOnly, RequireAuth, RequirePermission } from '@/components/guards'
import AppLayout from '@/layouts/AppLayout'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import DashboardPage from '@/pages/DashboardPage'
import AlertDetailPage from '@/pages/AlertDetailPage'
import CamerasPage from '@/pages/CamerasPage'
import PatrolsPage from '@/pages/PatrolsPage'
import RulesPage from '@/pages/RulesPage'
import ArchivePage from '@/pages/ArchivePage'
import StatsPage from '@/pages/StatsPage'
import AuditPage from '@/pages/AuditPage'
import SettingsPage from '@/pages/SettingsPage'
import { NotFoundPage, RouteErrorPage } from '@/pages/ErrorPages'
import { ReauthDialog } from '@/components/ReauthDialog'

const router = createBrowserRouter([
  // Landing and login are for guests; a signed-in user goes straight to /app.
  {
    element: <GuestOnly />,
    errorElement: <RouteErrorPage />,
    children: [
      { path: '/', element: <LandingPage /> },
      { path: '/login', element: <LoginPage /> },
    ],
  },

  // Authenticated Application Shell under /app
  {
    path: '/app',
    element: <RequireAuth />,
    errorElement: <RouteErrorPage />,
    children: [
      {
        element: <AppLayout />,
        children: [
          {
            element: <RequirePermission permission="dashboard.view" />,
            children: [{ index: true, element: <DashboardPage /> }],
          },
          {
            element: <RequirePermission permission="alerts.view" />,
            children: [
              { path: 'alerte', element: <Navigate to="/app" replace /> },
              { path: 'alerte/:id', element: <AlertDetailPage /> },
            ],
          },
          {
            element: <RequirePermission permission="cameras.view" />,
            children: [{ path: 'camere', element: <CamerasPage /> }],
          },
          {
            element: <RequirePermission permission="patrols.view" />,
            children: [{ path: 'patrule', element: <PatrolsPage /> }],
          },
          {
            element: <RequirePermission permission="rules.view" />,
            children: [{ path: 'reguli', element: <RulesPage /> }],
          },
          {
            element: <RequirePermission permission="archive.search" />,
            children: [{ path: 'arhiva', element: <ArchivePage /> }],
          },
          {
            element: <RequirePermission permission="stats.view" />,
            children: [{ path: 'statistici', element: <StatsPage /> }],
          },
          {
            element: <RequirePermission permission="audit.view" />,
            children: [{ path: 'audit', element: <AuditPage /> }],
          },
          {
            element: <RequirePermission permission="settings.admin" />,
            children: [{ path: 'setari', element: <SettingsPage /> }],
          },
        ],
      },
    ],
  },

  // Backward compatibility / redirects for flat routes
  { path: '/alerte', element: <Navigate to="/app" replace /> },
  { path: '/alerte/:id', element: <AlertRedirect /> },
  { path: '/camere', element: <Navigate to="/app/camere" replace /> },
  { path: '/patrule', element: <Navigate to="/app/patrule" replace /> },
  { path: '/reguli', element: <Navigate to="/app/reguli" replace /> },
  { path: '/arhiva', element: <Navigate to="/app/arhiva" replace /> },
  { path: '/statistici', element: <Navigate to="/app/statistici" replace /> },
  { path: '/audit', element: <Navigate to="/app/audit" replace /> },
  { path: '/setari', element: <Navigate to="/app/setari" replace /> },

  // 404 Catch-All
  { path: '*', element: <NotFoundPage /> },
])

function AlertRedirect() {
  const { id } = useParams()
  return <Navigate to={`/app/alerte/${id}`} replace />
}

export default function App() {
  return (
    <>
      <RouterProvider router={router} />
      <ReauthDialog />
    </>
  )
}
