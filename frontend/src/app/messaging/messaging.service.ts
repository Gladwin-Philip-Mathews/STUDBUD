import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface ConversationSummary {
  connectionId: number;
  other: { id: number; displayName: string };
  lastAt: string | null;
  unread: number;
  messages?: ChatMessage[];
}
export interface ChatMessage {
  id: number;
  text: string;
  sentAt: string;
  mine: boolean;
  status: string;
  notice?: string;
}
export interface SendResult {
  ok: boolean;
  message?: string;
  errors?: Record<string, string>;
}

@Injectable({ providedIn: 'root' })
export class MessagingService {
  private readonly http = inject(HttpClient);

  conversations(): Observable<ConversationSummary[]> {
    return this.http.get<{ conversations: ConversationSummary[] }>('/api/messages/conversations').pipe(map((r) => r.conversations));
  }
  open(connectionId: number): Observable<ConversationSummary | null> {
    return this.http.get<{ conversation: ConversationSummary }>(`/api/messages/conversations/${connectionId}`).pipe(
      map((r) => r.conversation),
      catchError(() => of(null))
    );
  }
  send(connectionId: number, text: string): Observable<SendResult> {
    return this.http.post(`/api/messages/conversations/${connectionId}`, { text }).pipe(
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of({ ok: false, message: e.error?.message, errors: e.error?.errors }))
    );
  }
}
