import { Routes } from '@angular/router';
import { adminGuard, authGuard } from './core/auth.guard';
import { AppShell } from './layout/app-shell/app-shell';
import { DashboardPage } from './pages/dashboard/dashboard';
import { LoginPage } from './pages/login/login';
import { NewResourcePage } from './pages/new-resource/new-resource';
import { MonitorDetailPage } from './pages/monitor-detail/monitor-detail';
import { RegisterUserPage } from './pages/register-user/register-user';
import { ResourceListPage } from './pages/resource-list/resource-list';
import { UserListPage } from './pages/user-list/user-list';

export const routes: Routes = [
  { path: 'login', component: LoginPage, title: 'Login · Monochrome' },
  {
    path: '',
    component: AppShell,
    canActivate: [authGuard],
    children: [
      { path: 'dashboard', component: DashboardPage, title: 'Dashboard · Monochrome' },
      {
        path: 'monitors/http/new',
        component: NewResourcePage,
        canActivate: [adminGuard],
        title: 'New HTTP monitor · Monochrome',
        data: { kind: 'http', title: 'New HTTP monitor', backUrl: '/monitors/http' },
      },
      {
        path: 'monitors/http/:id',
        component: MonitorDetailPage,
        canActivate: [adminGuard],
        data: { backUrl: '/monitors/http' },
      },
      {
        path: 'monitors/http',
        component: ResourceListPage,
        canActivate: [adminGuard],
        data: {
          title: 'HTTP monitors',
          description: 'Website and HTTP endpoint availability checks.',
          endpoint: '/HTTP_monitors/list_all',
          newUrl: '/monitors/http/new',
          detailBase: '/monitors/http',
          deletePath: '/HTTP_monitors/:id/delete',
          updatePath: '/HTTP_monitors/:id/update',
        },
      },
      {
        path: 'monitors/api/new',
        component: NewResourcePage,
        canActivate: [adminGuard],
        title: 'New API monitor · Monochrome',
        data: { kind: 'api', title: 'New API monitor', backUrl: '/monitors/api' },
      },
      {
        path: 'monitors/api/:id',
        component: MonitorDetailPage,
        canActivate: [adminGuard],
        data: { backUrl: '/monitors/api' },
      },
      {
        path: 'monitors/api',
        component: ResourceListPage,
        canActivate: [adminGuard],
        data: {
          title: 'API monitors',
          description: 'Request, response, and protected API checks.',
          endpoint: '/API_monitors/list_all',
          newUrl: '/monitors/api/new',
          detailBase: '/monitors/api',
          deletePath: '/API_monitors/:id',
          updatePath: '/API_monitors/:id',
        },
      },
      {
        path: 'monitors/ping/new',
        component: NewResourcePage,
        canActivate: [adminGuard],
        title: 'New Ping monitor · Monochrome',
        data: { kind: 'ping', title: 'New Ping monitor', backUrl: '/monitors/ping' },
      },
      {
        path: 'monitors/ping/:id',
        component: MonitorDetailPage,
        canActivate: [adminGuard],
        data: { backUrl: '/monitors/ping' },
      },
      {
        path: 'monitors/ping',
        component: ResourceListPage,
        canActivate: [adminGuard],
        data: {
          title: 'Ping monitors',
          description: 'Operating-system ICMP host checks.',
          endpoint: '/ping-monitors/list_all',
          newUrl: '/monitors/ping/new',
          detailBase: '/monitors/ping',
          deletePath: '/ping-monitors/:id/delete',
          updatePath: '/ping-monitors/:id/update',
        },
      },
      {
        path: 'monitors/heartbeat/new',
        component: NewResourcePage,
        canActivate: [adminGuard],
        title: 'New Heartbeat monitor · Monochrome',
        data: {
          kind: 'heartbeat',
          title: 'New Heartbeat monitor',
          backUrl: '/monitors/heartbeat',
        },
      },
      {
        path: 'monitors/heartbeat/:id',
        component: MonitorDetailPage,
        canActivate: [adminGuard],
        data: { backUrl: '/monitors/heartbeat' },
      },
      {
        path: 'monitors/heartbeat',
        component: ResourceListPage,
        canActivate: [adminGuard],
        data: {
          title: 'Heartbeat monitors',
          description: 'Passive client heartbeat listeners.',
          endpoint: '/heartbeat-monitors/list_all',
          newUrl: '/monitors/heartbeat/new',
          detailBase: '/monitors/heartbeat',
          deletePath: '/heartbeat-monitors/:id/delete',
          updatePath: '/heartbeat-monitors/:id/update',
        },
      },
      {
        path: 'auth-profiles/new',
        component: NewResourcePage,
        canActivate: [adminGuard],
        title: 'New auth profile · Monochrome',
        data: { kind: 'auth-profile', title: 'New auth profile', backUrl: '/auth-profiles' },
      },
      {
        path: 'auth-profiles',
        component: ResourceListPage,
        canActivate: [adminGuard],
        data: {
          title: 'Auth profiles',
          description: 'Credentials used by protected API monitors.',
          endpoint: '/auth-profiles/list_all',
          newUrl: '/auth-profiles/new',
          deletePath: '/auth-profiles/:id',
        },
      },
      {
        path: 'users/new',
        component: RegisterUserPage,
        canActivate: [adminGuard],
        title: 'Register user · Monochrome',
      },
      {
        path: 'users',
        component: UserListPage,
        canActivate: [adminGuard],
        title: 'Registered users · Monochrome',
      },
      { path: 'register', pathMatch: 'full', redirectTo: 'users/new' },
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
    ],
  },
  { path: '**', redirectTo: 'dashboard' },
];
