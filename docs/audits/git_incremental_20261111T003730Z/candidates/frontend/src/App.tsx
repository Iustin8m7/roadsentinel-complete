import { ReauthDialog } from '@/components/ReauthDialog'
import { createBrowserRouter, Navigate, RouterProvider, useParams } from 'react-router'
import { GuestOnly, RequireAuth, RequirePermission } from '@/components/guards'
import AppLayout from '@/layouts/AppLayout'
import LandingPage from '@/pages/LandingPage'
import LoginPage from '@/pages/LoginPage'
import { NotFoundPage, RouteErrorPage } from '@/pages/ErrorPages'

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
            children: [{ index: true, lazy: () => import('@/pages/DashboardPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="alerts.view" />,
            children: [
              { path: 'alerte', element: <Navigate to="/app" replace /> },
              { path: 'alerte/:id', lazy: () => import('@/pages/AlertDetailPage').then((m) => ({ Component: m.default })) },
            ],
          },
          {
            element: <RequirePermission permission="cameras.view" />,
            children: [{ path: 'camere', lazy: () => import('@/pages/CamerasPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="video-analysis.view" />,
            children: [{ path: 'analiza-video', lazy: () => import('@/pages/VideoAnalysisPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="patrols.view" />,
            children: [{ path: 'patrule', lazy: () => import('@/pages/PatrolsPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="rules.view" />,
            children: [{ path: 'reguli', lazy: () => import('@/pages/RulesPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="archive.search" />,
            children: [{ path: 'arhiva', lazy: () => import('@/pages/ArchivePage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="stats.view" />,
            children: [{ path: 'statistici', lazy: () => import('@/pages/StatsPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="audit.view" />,
            children: [{ path: 'audit', lazy: () => import('@/pages/AuditPage').then((m) => ({ Component: m.default })) }],
          },
          {
            element: <RequirePermission permission="settings.admin" />,
            children: [{ path: 'setari', lazy: () => import('@/pages/SettingsPage').then((m) => ({ Component: m.default })) }],
          },
        ],
      },
    ],
  },

  // Backward compatibility / redirects for flat routes
  { path: '/alerte', element: <Navigate to="/app" replace /> },
  { path: '/alerte/:id', element: <AlertRedirect /> },
  { path: '/camere', element: <Navigate to="/app/camere" replace /> },
  { path: '/analiza-video', element: <Navigate to="/app/analiza-video" replace /> },
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
  return <><RouterProvider router={router} /><ReauthDialog /></>
}
