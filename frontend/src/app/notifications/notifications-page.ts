import { Component, OnInit, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { AppNotification, NotificationsService } from './notifications.service';

@Component({
  selector: 'app-notifications-page',
  template: `
    <h2>Notifications</h2>
    <p>
      <button type="button" id="read-all" (click)="readAll()">Mark all as read</button>
      <label><input type="checkbox" [checked]="emailOn()" (change)="toggleEmail($event)" /> Email me too</label>
    </p>
    @for (n of items(); track n.id) {
      <div class="item" [class.unread]="!n.read">
        <button type="button" class="link" (click)="open(n)">{{ n.body }}</button>
        <small>{{ n.createdAt }}</small>
      </div>
    } @empty { <p>Nothing yet.</p> }
  `,
  styles: `.item { background: var(--white); border: 1px solid var(--line); border-radius: 10px; padding: .6rem .9rem; margin: .45rem 0; } .item.unread { border-left: 4px solid var(--orange); } .unread { font-weight: 600; } .link { background: none; border: 0; text-align: left; padding: 0; font: inherit; cursor: pointer; } small { display: block; }`,
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
