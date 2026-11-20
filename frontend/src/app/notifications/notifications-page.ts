import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AppNotification, NotificationsService } from './notifications.service';

@Component({
  selector: 'app-notifications-page',
  template: `
    <div class="page-head">
      <h2>Notifications</h2>
      <p class="lead">Replies, requests and messages for you. Open one to go to it.</p>
    </div>
    <div class="actions">
      <button type="button" id="read-all" (click)="readAll()">Mark all as read</button>
      <label class="check"><input type="checkbox" [checked]="emailOn()" (change)="toggleEmail($event)" /> Email me too</label>
    </div>
    @for (n of items(); track n.id) {
      <div class="item" [class.unread]="!n.read">
        <button type="button" class="link" (click)="open(n)">{{ n.body }}</button>
        <small>{{ n.createdAt.slice(0, 16).replace('T', ' ') }}</small>
      </div>
    } @empty { <p class="empty">Nothing yet.</p> }
  `,
  styles: `.item { display: flex; justify-content: space-between; gap: 1rem; align-items: center; background: var(--white); border: 1px solid var(--line); border-radius: 12px; padding: .65rem 1rem; margin: .5rem 0; box-shadow: var(--shadow-sm); } .item.unread { border-left: 4px solid var(--orange); background: var(--orange-tint); } .unread .link { font-weight: 700; } .link { text-align: left; color: var(--ink); text-decoration: none; padding: 0; } .link:hover { color: var(--orange-ink); text-decoration: underline; } .actions { margin: 0 0 .75rem; }`,
})
export class NotificationsPage implements OnInit {
  private readonly api = inject(NotificationsService);
  readonly items = signal<AppNotification[]>([]);
  readonly emailOn = signal(true);

  ngOnInit(): void {
    this.load();
  }

  private readonly router = inject(Router);

  load(): void {
    this.api.list().subscribe((r) => {
      this.items.set(r.notifications);
      if (typeof r.email === 'boolean') this.emailOn.set(r.email); // FR-082: the stored choice, not a default
    });
  }

  /** Opening a notification marks it read and goes to the item it is about (DF-27). */
  open(n: AppNotification): void {
    const link = this.api.linkFor(n);
    const go = () => { if (link) void this.router.navigate(link); };
    if (!n.read) {
      this.api.markRead(n.id).subscribe(() => { this.load(); go(); });
    } else {
      go();
    }
  }

  readAll(): void {
    this.api.markAllRead().subscribe(() => this.load());
  }

  toggleEmail(event: Event): void {
    const on = (event.target as HTMLInputElement).checked;
    this.emailOn.set(on);
    this.api.setEmail(on).subscribe();
  }
}
