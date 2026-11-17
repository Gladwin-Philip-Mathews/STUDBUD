import { Injectable, inject, signal } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';

export interface Account {
  id: number;
  email: string;
  displayName: string;
  role: string;
}

export interface ApiResult {
  ok: boolean;
  message?: string;
  errors?: Record<string, string>;
  canResend?: boolean;
}

function toResult(e: HttpErrorResponse): ApiResult {
  const body = e.error ?? {};
  return { ok: false, message: body.message, errors: body.errors, canResend: body.canResend };
}

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);
  readonly account = signal<Account | null>(null);

  register(email: string, displayName: string, password: string): Observable<ApiResult> {
    return this.http.post<{ message: string }>('/api/auth/register', { email, displayName, password }).pipe(
      map((r) => ({ ok: true, message: r.message })),
      catchError((e: HttpErrorResponse) => of(toResult(e)))
    );
  }

  verify(token: string): Observable<ApiResult> {
    return this.http.post<{ message: string }>('/api/auth/verify', { token }).pipe(
      map((r) => ({ ok: true, message: r.message })),
      catchError((e: HttpErrorResponse) => of(toResult(e)))
    );
  }

  resend(email: string): Observable<ApiResult> {
    return this.http.post<{ message: string }>('/api/auth/resend', { email }).pipe(
      map((r) => ({ ok: true, message: r.message })),
      catchError((e: HttpErrorResponse) => of(toResult(e)))
    );
  }

  signIn(email: string, password: string): Observable<ApiResult> {
    return this.http.post<{ account: Account }>('/api/auth/sign-in', { email, password }).pipe(
      tap((r) => this.account.set(r.account)),
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of(toResult(e)))
    );
  }

  signOut(): Observable<void> {
    return this.http.post('/api/auth/sign-out', {}).pipe(
      tap(() => this.account.set(null)),
      map(() => undefined)
    );
  }

  /** Asks the backend who is signed in. Used by the route guard (the backend decides, NFR-013). */
  loadMe(): Observable<Account | null> {
    return this.http.get<{ account: Account }>('/api/auth/me').pipe(
      map((r) => r.account),
      catchError(() => of(null)),
      tap((a) => this.account.set(a))
    );
  }
}
