import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { map } from 'rxjs';
import { AuthService } from './auth.service';

export const authGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.loadMe().pipe(map((a) => (a ? true : router.createUrlTree(['/sign-in']))));
};

/** FR-010: a signed-in student without a profile is sent to the profile page first. */
export const profileGuard: CanActivateFn = () => {
  const auth = inject(AuthService);
  const router = inject(Router);
  return auth.loadMe().pipe(
    map((a) => (!a ? router.createUrlTree(['/sign-in']) : auth.profileComplete() ? true : router.createUrlTree(['/profiles'])))
  );
};
