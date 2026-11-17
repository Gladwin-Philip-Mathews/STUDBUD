import { Component, inject } from '@angular/core';
import { AuthService } from './auth.service';

/** Replaced by the real profile page in Phase 3. */
@Component({
  selector: 'app-profile-placeholder',
  template: `<h2>Welcome, {{ auth.account()?.displayName }}</h2><p>Profile creation comes next.</p>`,
})
export class ProfilePlaceholder {
  protected readonly auth = inject(AuthService);
}
