import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NotificationsService } from '../notifications/notifications.service';
import { Connected, ConnectionsService, RequestItem, Suggestion } from './connections.service';

@Component({
  selector: 'app-connections-home',
  imports: [FormsModule],
  template: `
    <h2>Connections</h2>
    @if (message()) { <p class="notice" id="conn-message" role="status">{{ message() }}</p> }

    <h3>Requests for you</h3>
    @for (r of incoming(); track r.id) {
      <div class="row">
        <span><strong>{{ r.other.displayName }}</strong> @if (r.note) { <em>"{{ r.note }}"</em> }</span>
        <button type="button" class="accept" (click)="act(r.id, 'accept')">Accept</button>
        <button type="button" class="decline" (click)="act(r.id, 'decline')">Decline</button>
      </div>
    } @empty { <p>No requests.</p> }

    <h3>Your sent requests</h3>
    @for (r of outgoing(); track r.id) {
      <div class="row">
        <span>{{ r.other.displayName }} (pending)</span>
        <button type="button" (click)="act(r.id, 'withdraw')">Withdraw</button>
      </div>
    } @empty { <p>None pending.</p> }

    <h3>Your connections</h3>
    @for (c of accepted(); track c.connectionId) {
      <div class="row">
        <span><strong>{{ c.displayName }}</strong> {{ shared(c) }}</span>
        <button type="button" (click)="act(c.connectionId, 'remove')">Remove</button>
      </div>
    } @empty { <p>No connections yet.</p> }

    <h3>Suggested for you</h3>
    @for (s of suggestions(); track s.accountId) {
      <div class="row suggestion">
        <span><strong>{{ s.displayName }}</strong> ({{ s.intent }}) {{ shared(s) }}</span>
        <input [(ngModel)]="notes[s.accountId]" [name]="'note' + s.accountId" maxlength="200" aria-label="Optional note to {{ s.displayName }}" placeholder="Optional note" />
        <button type="button" class="send" (click)="send(s)">Send request</button>
        <button type="button" (click)="dismiss(s)">Dismiss</button>
      </div>
    } @empty { <p>No suggestions yet. Complete your profile to see some.</p> }
  `,
  styles: `.row { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; margin: .35rem 0; } .row span { flex: 1; }`,
})
export class ConnectionsHome implements OnInit {
  private readonly api = inject(ConnectionsService);
  private readonly notifications = inject(NotificationsService);
  readonly suggestions = signal<Suggestion[]>([]);
  readonly accepted = signal<Connected[]>([]);
  readonly incoming = signal<RequestItem[]>([]);
  readonly outgoing = signal<RequestItem[]>([]);
  readonly message = signal('');
  notes: Record<number, string> = {};

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.api.suggestions().subscribe((x) => this.suggestions.set(x));
    this.api.accepted().subscribe((x) => this.accepted.set(x));
    this.api.incoming().subscribe((x) => this.incoming.set(x));
    this.api.outgoing().subscribe((x) => this.outgoing.set(x));
    this.notifications.refresh();
  }

  shared(x: { sharedCourses: string[]; sharedInterests: string[] }): string {
    const all = [...x.sharedCourses, ...x.sharedInterests];
    return all.length ? `Shared: ${all.join(', ')}` : '';
  }

  send(s: Suggestion): void {
    this.api.sendRequest(s.accountId, this.notes[s.accountId] ?? '').subscribe((r) => {
      this.message.set(r.ok ? `Request sent to ${s.displayName}.` : (r.message ?? ''));
      this.reload();
    });
  }

  dismiss(s: Suggestion): void {
    this.api.dismiss(s.accountId).subscribe(() => this.reload());
  }

  act(id: number, action: 'accept' | 'decline' | 'withdraw' | 'remove'): void {
    this.api.act(id, action).subscribe((r) => {
      this.message.set(r.ok ? '' : (r.message ?? ''));
      this.reload();
    });
  }
}
