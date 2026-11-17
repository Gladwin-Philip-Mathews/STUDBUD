import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from './auth.service';

describe('AuthService', () => {
  let auth: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    auth = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  it('returns field errors from a rejected registration', () => {
    let result: any;
    auth.register('a@x.com', 'Ana', 'pw').subscribe((r) => (result = r));
    http.expectOne('/api/auth/register').flush(
      { errors: { email: 'Only RIT email addresses are accepted.' } },
      { status: 400, statusText: 'Bad Request' }
    );
    expect(result.ok).toBeFalse();
    expect(result.errors.email).toContain('RIT');
  });

  it('stores the account after a successful sign in', () => {
    auth.signIn('a@g.rit.edu', 'passw0rdX').subscribe();
    http.expectOne('/api/auth/sign-in').flush({
      account: { id: 1, email: 'a@g.rit.edu', displayName: 'Ana', role: 'student' },
    });
    expect(auth.account()?.displayName).toBe('Ana');
  });

  it('keeps the same message for a wrong password and flags a resend offer when unverified', () => {
    let result: any;
    auth.signIn('a@g.rit.edu', 'x').subscribe((r) => (result = r));
    http.expectOne('/api/auth/sign-in').flush(
      { message: 'Please verify your email first.', canResend: true },
      { status: 403, statusText: 'Forbidden' }
    );
    expect(result.canResend).toBeTrue();
    expect(auth.account()).toBeNull();
  });

  it('clears the account on sign out', () => {
    auth.account.set({ id: 1, email: 'a', displayName: 'A', role: 'student' });
    auth.signOut().subscribe();
    http.expectOne('/api/auth/sign-out').flush({});
    expect(auth.account()).toBeNull();
  });
});
