import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-sign-in',
  imports: [FormsModule, RouterLink],
  template: `
    <h2>Sign in</h2>
    <form (ngSubmit)="submit()" novalidate>
      <label>Email <input name="email" type="email" [(ngModel)]="email" autocomplete="email" /></label>
      <label>Password
        <input name="password" type="password" [(ngModel)]="password" autocomplete="current-password" />
      </label>
      <button type="submit" [disabled]="busy()">Sign in</button>
    </form>
    @if (error()) { <p class="error" id="sign-in-error">{{ error() }}</p> }
    @if (canResend()) {
      <button type="button" id="resend" (click)="resend()">Send a new verification message</button>
    }
    @if (info()) { <p class="notice" id="sign-in-info">{{ info() }}</p> }
    <p>New here? <a routerLink="/register">Create an account</a></p>
  `,
})
export class SignIn {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  email = '';
  password = '';
  readonly error = signal('');
  readonly info = signal('');
  readonly canResend = signal(false);
  readonly busy = signal(false);

  submit(): void {
    this.busy.set(true);
    this.error.set('');
    this.auth.signIn(this.email, this.password).subscribe((r) => {
      this.busy.set(false);
      if (r.ok) {
        this.router.navigateByUrl('/profile');
      } else {
        this.error.set(r.message ?? 'Sign in failed.');
        this.canResend.set(!!r.canResend);
      }
    });
  }

  resend(): void {
    this.auth.resend(this.email).subscribe((r) => this.info.set(r.message ?? ''));
  }
}
