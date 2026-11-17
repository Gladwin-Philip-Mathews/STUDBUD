import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { Register } from './auth/register';
import { SignIn } from './auth/sign-in';
import { NotificationsPage } from './notifications/notifications-page';
import { Verify } from './auth/verify';

// Each feature lives in its own folder and loads on demand. Teammates edit only their own
// <feature>/<feature>.routes.ts, not this file.
const feature = (path: string, load: () => Promise<{ routes: Routes }>) => ({
  path,
  canActivate: [authGuard],
  loadChildren: () => load().then((m) => m.routes),
});

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'sign-in' },
  { path: 'register', component: Register },
  { path: 'verify', component: Verify },
  { path: 'sign-in', component: SignIn },
  { path: 'profile', pathMatch: 'full', redirectTo: 'profiles' },
  feature('profiles', () => import('./profiles/profiles.routes')),
  feature('communities', () => import('./communities/communities.routes')),
  feature('connections', () => import('./connections/connections.routes')),
  { path: 'notifications', component: NotificationsPage, canActivate: [authGuard] },
  feature('messaging', () => import('./messaging/messaging.routes')),
  feature('moderation', () => import('./moderation/moderation.routes')),
  feature('admin', () => import('./admin/admin.routes')),
  { path: '**', redirectTo: 'sign-in' },
];
