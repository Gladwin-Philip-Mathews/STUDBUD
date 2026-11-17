import { Routes } from '@angular/router';
import { authGuard } from './auth/auth.guard';
import { ProfilePlaceholder } from './auth/profile-placeholder';
import { Register } from './auth/register';
import { SignIn } from './auth/sign-in';
import { Verify } from './auth/verify';

export const routes: Routes = [
  { path: '', pathMatch: 'full', redirectTo: 'sign-in' },
  { path: 'register', component: Register },
  { path: 'verify', component: Verify },
  { path: 'sign-in', component: SignIn },
  { path: 'profile', component: ProfilePlaceholder, canActivate: [authGuard] },
  { path: '**', redirectTo: 'sign-in' },
];
