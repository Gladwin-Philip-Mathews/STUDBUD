import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export const REPORT_REASONS = ['harassment', 'spam', 'unsafe or inappropriate content', 'academic integrity', 'other'];
export const DECISIONS = ['upheld', 'dismissed'];
export const ACTIONS = ['none', 'warning', 'content hidden', 'account suspended'];

export interface QueueReport {
  id: number;
  reason: string;
  text: string;
  status: string;
  ageHours: number;
  overdue: boolean;
  receivedAt: string;
  reporter: string;
  reportedStudent: string;
  itemType: string;
  item: { type: string; title?: string; text?: string; status?: string } | null;
  acknowledgedAt: string | null;
}
export interface Outcome {
  ok: boolean;
  message?: string;
  errors?: Record<string, string>;
  data?: Record<string, unknown>;
}

function failed(e: HttpErrorResponse): Outcome {
  return { ok: false, message: e.error?.message, errors: e.error?.errors };
}

@Injectable({ providedIn: 'root' })
export class ModerationService {
  private readonly http = inject(HttpClient);

  /** A student reports a student, post, reply or message (FR-060). */
  report(itemType: string, itemId: number, reason: string, text: string): Observable<Outcome> {
    return this.http.post<{ message: string }>('/api/reports', { itemType, itemId, reason, text }).pipe(
      map((r) => ({ ok: true, message: r.message })),
      catchError((e: HttpErrorResponse) => of(failed(e)))
    );
  }
  queue(): Observable<QueueReport[]> {
    return this.http.get<{ reports: QueueReport[] }>('/api/moderation/queue').pipe(map((r) => r.reports));
  }
  acknowledge(id: number): Observable<Outcome> {
    return this.http.post(`/api/moderation/reports/${id}/acknowledge`, {}).pipe(map(() => ({ ok: true })), catchError((e) => of(failed(e))));
  }
  decide(id: number, decision: string, action: string, note: string): Observable<Outcome> {
    return this.http.post(`/api/moderation/reports/${id}/decision`, { decision, action, note }).pipe(
      map(() => ({ ok: true })),
      catchError((e) => of(failed(e)))
    );
  }
  summary(id: number): Observable<Outcome> {
    return this.http.get<{ summary: Record<string, unknown> }>(`/api/moderation/reports/${id}/summary`).pipe(
      map((r) => ({ ok: true, data: r.summary })),
      catchError((e) => of(failed(e)))
    );
  }
}
