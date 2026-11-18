import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-register',
  imports: [FormsModule, RouterLink],
  template: `
    <h2>Create your account</h2>
    <form (ngSubmit)="submit()" #f="ngForm" novalidate>
      <label>RIT email
        <input name="email" type="email" [(ngModel)]="email" autocomplete="email" />
      </label>
      @if (errors()['email']) { <p class="error" id="email-error">{{ errors()['email'] }}</p> }

      <label>Display name
        <input name="displayName" [(ngModel)]="displayName" />
      </label>
      @if (errors()['displayName']) { <p class="error" id="name-error">{{ errors()['displayName'] }}</p> }

      <label>Password
        <input name="password" type="password" [(ngModel)]="password" autocomplete="new-password" />
      </label>
      @if (errors()['password']) { <p class="error" id="password-error">{{ errors()['password'] }}</p> }

      <section class="notice-box" id="conduct-notice">
        <p><strong>Conduct and privacy notice</strong></p>
        <p>Posts and messages must follow the RIT conduct rules. Harassment and intimidation are conduct violations in every channel and can be reported.</p>
        <p>StudBud stores your RIT email, display name, profile, posts, messages and connections. Other students see only your display name, interests, courses and connection intent. Moderators can read a message only through a safety report. Nothing is shared with outside parties.</p>
      </section>
      <label class="check"><input name="acceptNotice" type="checkbox" [(ngModel)]="acceptNotice" /> I accept this notice</label>
      @if (errors()['acceptNotice']) { <p class="error" id="notice-error">{{ errors()['acceptNotice'] }}</p> }

      <button type="submit" [disabled]="busy()">Register</button>
    </form>
    @if (message()) { <p class="notice" id="register-message">{{ message() }}</p> }
    <p>Already registered? <a routerLink="/sign-in">Sign in</a></p>
  `,
})
export class Register {
  private readonly auth = inject(AuthService);
  email = '';
  displayName = '';
  password = '';
  acceptNotice = false;
  readonly errors = signal<Record<string, string>>({});
  readonly message = signal('');
  readonly busy = signal(false);

  submit(): void {
    this.busy.set(true);
    this.auth.register(this.email, this.displayName, this.password, this.acceptNotice).subscribe((r) => {
      this.busy.set(false);
      this.errors.set(r.errors ?? {});
      this.message.set(r.ok ? (r.message ?? '') : '');
    });
  }
}
