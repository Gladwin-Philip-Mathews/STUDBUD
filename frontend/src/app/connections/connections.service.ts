import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface Suggestion {
  accountId: number;
  displayName: string;
  intent: string;
  sharedCourses: string[];
  sharedInterests: string[];
}
export interface Connected {
  connectionId: number;
  accountId: number;
  displayName: string;
  sharedCourses: string[];
  sharedInterests: string[];
}
export interface RequestItem {
  id: number;
  note: string;
  other: { id: number; displayName: string };
}
export interface Result {
  ok: boolean;
  message?: string;
}

@Injectable({ providedIn: 'root' })
export class ConnectionsService {
  private readonly http = inject(HttpClient);

  suggestions(): Observable<Suggestion[]> {
    return this.http.get<{ suggestions: Suggestion[] }>('/api/connections/suggestions').pipe(map((r) => r.suggestions));
  }
  accepted(): Observable<Connected[]> {
    return this.http.get<{ connections: Connected[] }>('/api/connections').pipe(map((r) => r.connections));
  }
  incoming(): Observable<RequestItem[]> {
    return this.http.get<{ requests: RequestItem[] }>('/api/connections/incoming').pipe(map((r) => r.requests));
  }
  outgoing(): Observable<RequestItem[]> {
    return this.http.get<{ requests: RequestItem[] }>('/api/connections/outgoing').pipe(map((r) => r.requests));
  }

  sendRequest(receiverId: number, note: string): Observable<Result> {
    return this.http.post('/api/connections/requests', { receiverId, note }).pipe(
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of({ ok: false, message: e.error?.message ?? 'Request failed.' }))
    );
  }
  dismiss(accountId: number): Observable<unknown> {
    return this.http.post(`/api/connections/suggestions/${accountId}/dismiss`, {});
  }
  act(id: number, action: 'accept' | 'decline' | 'withdraw' | 'remove'): Observable<Result> {
    return this.http.post(`/api/connections/${id}/${action}`, {}).pipe(
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of({ ok: false, message: e.error?.message ?? 'Action failed.' }))
    );
  }
}
