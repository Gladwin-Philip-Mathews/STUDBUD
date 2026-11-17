import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { AuthService } from './auth.service';

@Component({
  selector: 'app-verify',
  imports: [FormsModule, RouterLink],
  template: `
    <h2>Verify your account</h2>
    @if (state() === 'checking') { <p>Checking your link...</p> }
    @if (state() === 'ok') {
      <p class="notice" id="verify-ok">{{ message() }}</p>
      <a routerLink="/sign-in">Continue to sign in</a>
    }
    @if (state() === 'failed') {
      <p class="error" id="verify-failed">{{ message() }}</p>
      <label>Your email <input name="email" type="email" [(ngModel)]="email" /></label>
      <button type="button" id="resend" (click)="resend()">Send a new verification message</button>
      @if (info()) { <p class="notice">{{ info() }}</p> }
    }
  `,
})
export class Verify implements OnInit {
  private readonly auth = inject(AuthService);
  private readonly route = inject(ActivatedRoute);
  readonly state = signal<'checking' | 'ok' | 'failed'>('checking');
  readonly message = signal('');
  readonly info = signal('');
  email = '';

  ngOnInit(): void {
    const token = this.route.snapshot.queryParamMap.get('token') ?? '';
    this.auth.verify(token).subscribe((r) => {
      this.message.set(r.message ?? '');
      this.state.set(r.ok ? 'ok' : 'failed');
    });
  }

  resend(): void {
    this.auth.resend(this.email).subscribe((r) => this.info.set(r.message ?? ''));
  }
}
