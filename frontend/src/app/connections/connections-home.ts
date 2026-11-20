import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Avatar } from '../shared/avatar';
import { Section, Sections } from '../shared/sections';
import { NotificationsService } from '../notifications/notifications.service';
import { Connected, ConnectionsService, RequestItem, Suggestion } from './connections.service';

@Component({
  selector: 'app-connections-home',
  imports: [FormsModule, Sections, Avatar],
  template: `
    <div class="page-head">
      <h2>Connections</h2>
      <p class="lead">Find students to study with and keep track of your requests.</p>
    </div>
    @if (message()) { <p class="notice" id="conn-message" role="status">{{ message() }}</p> }

    <app-sections [sections]="sectionList()" [(active)]="section" label="Connections sections">
      @if (section() === 'suggested') {
        <h3>Suggested for you</h3>
        @for (s of suggestions(); track s.accountId) {
          <div class="row suggestion">
            <app-avatar [name]="s.displayName" [size]="2.5" />
            <span><strong>{{ s.displayName }}</strong> <span class="kind">{{ s.intent }}</span><br /><small>{{ shared(s) }}</small></span>
            <input [(ngModel)]="notes[s.accountId]" [name]="'note' + s.accountId" maxlength="200" aria-label="Optional note to {{ s.displayName }}" placeholder="Optional note" />
            <button type="button" class="send" (click)="send(s)">Send request</button>
            <button type="button" class="btn-small" (click)="dismiss(s)">Dismiss</button>
          </div>
        } @empty { <p class="empty">No suggestions yet. Complete your profile to see some.</p> }
      }

      @if (section() === 'requests') {
        <h3>Requests for you</h3>
        @for (r of incoming(); track r.id) {
          <div class="row">
            <app-avatar [name]="r.other.displayName" [size]="2.5" />
            <span><strong>{{ r.other.displayName }}</strong> @if (r.note) { <br /><em>"{{ r.note }}"</em> }</span>
            <button type="button" class="accept" (click)="act(r.id, 'accept')">Accept</button>
            <button type="button" class="decline" (click)="act(r.id, 'decline')">Decline</button>
          </div>
        } @empty { <p class="empty">No requests.</p> }
      }

      @if (section() === 'sent') {
        <h3>Your sent requests</h3>
        @for (r of outgoing(); track r.id) {
          <div class="row">
            <app-avatar [name]="r.other.displayName" [size]="2.5" />
            <span>{{ r.other.displayName }} <small>(pending)</small></span>
            <button type="button" class="btn-small" (click)="act(r.id, 'withdraw')">Withdraw</button>
          </div>
        } @empty { <p class="empty">None pending.</p> }
      }

      @if (section() === 'connected') {
        <h3>Your connections</h3>
        @for (c of accepted(); track c.connectionId) {
          <div class="row">
            <app-avatar [name]="c.displayName" [size]="2.5" />
            <span><strong>{{ c.displayName }}</strong><br /><small>{{ shared(c) }}</small></span>
            <button type="button" class="btn-small" (click)="act(c.connectionId, 'remove')">Remove</button>
          </div>
        } @empty { <p class="empty">No connections yet.</p> }
      }
    </app-sections>
  `,
  styles: `.suggestion input { flex: 1; min-width: 10rem; max-width: 16rem; }`,
})
export class ConnectionsHome implements OnInit {
  private readonly api = inject(ConnectionsService);
  private readonly notifications = inject(NotificationsService);
  readonly suggestions = signal<Suggestion[]>([]);
  readonly accepted = signal<Connected[]>([]);
  readonly incoming = signal<RequestItem[]>([]);
  readonly outgoing = signal<RequestItem[]>([]);
  readonly message = signal('');
  readonly section = signal('suggested');
  readonly sectionList = computed<Section[]>(() => [
    { id: 'suggested', label: 'Suggested' },
    { id: 'requests', label: 'Requests', count: this.incoming().length },
    { id: 'sent', label: 'Sent' },
    { id: 'connected', label: 'Connected' },
  ]);
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
