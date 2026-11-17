import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of, tap } from 'rxjs';

export interface AppNotification {
  id: number;
  event: string;
  body: string;
  createdAt: string;
  read: boolean;
}

@Injectable({ providedIn: 'root' })
export class NotificationsService {
  private readonly http = inject(HttpClient);
  /** Shown on every page (FR-080). */
  readonly unread = signal(0);

  refresh(): void {
    this.http.get<{ unread: number }>('/api/notifications/unread-count').pipe(catchError(() => of({ unread: 0 })))
      .subscribe((r) => this.unread.set(r.unread));
  }

  list(): Observable<{ notifications: AppNotification[]; unread: number }> {
    return this.http.get<{ notifications: AppNotification[]; unread: number }>('/api/notifications').pipe(
      tap((r) => this.unread.set(r.unread))
    );
  }

  markRead(id: number): Observable<unknown> {
    return this.http.post(`/api/notifications/${id}/read`, {}).pipe(tap(() => this.refresh()));
  }

  markAllRead(): Observable<unknown> {
    return this.http.post('/api/notifications/read-all', {}).pipe(tap(() => this.refresh()));
  }

  setEmail(enabled: boolean): Observable<unknown> {
    return this.http.put('/api/notifications/settings', { email: enabled });
  }
}
