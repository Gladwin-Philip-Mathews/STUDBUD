import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, of, tap } from 'rxjs';

export interface AppNotification {
  id: number;
  event: string;
  body: string;
  createdAt: string;
  read: boolean;
  /** DR-011: the post, connection, conversation or report the event is about. */
  item: { type: string; id: number } | null;
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

  list(): Observable<{ notifications: AppNotification[]; unread: number; email?: boolean }> {
    return this.http.get<{ notifications: AppNotification[]; unread: number; email?: boolean }>('/api/notifications').pipe(
      tap((r) => this.unread.set(r.unread))
    );
  }

  /** Where a notification leads (DF-27 → the item of DR-011). */
  linkFor(n: AppNotification): string[] | null {
    switch (n.item?.type) {
      case 'post': return ['/communities', 'post', String(n.item.id)];
      case 'connection': return ['/connections'];
      case 'conversation': return ['/messaging'];
      default: break;
    }
    // Notifications made before the item was stored have no item; the event still says where to go.
    switch (n.event) {
      case 'REPLY_ADDED': return ['/communities'];
      case 'REQUEST_RECEIVED':
      case 'REQUEST_ANSWERED': return ['/connections'];
      case 'MESSAGE_RECEIVED': return ['/messaging'];
      default: return null;
    }
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
