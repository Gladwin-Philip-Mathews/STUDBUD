import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReportForm } from '../moderation/report-form';
import { ChatMessage, ConversationSummary, MessagingService } from './messaging.service';

@Component({
  selector: 'app-messaging-home',
  imports: [FormsModule, ReportForm],
  template: `
    <h2>Messages</h2>
    <div class="layout">
      <nav>
        @for (c of conversations(); track c.connectionId) {
          <button type="button" class="conv" [class.active]="c.connectionId === currentId()" (click)="open(c)">
            {{ c.other.displayName }} @if (c.unread) { <span class="badge">{{ c.unread }}</span> }
          </button>
        } @empty { <p>No connections yet. Accept or send a connection request first.</p> }
      </nav>
      <section>
        @if (currentId()) {
          @for (m of messages(); track m.id) {
            <p class="msg" [class.mine]="m.mine"><strong>{{ m.mine ? 'You' : currentName() }}:</strong> {{ m.text }}
              <small>{{ m.sentAt.slice(11, 16) }}</small>
              @if (m.notice) { <small class="notice">{{ m.notice }}</small> }
              @if (!m.mine) { <app-report-form itemType="message" [itemId]="m.id" /> }
            </p>
          } @empty { <p>No messages yet. Say hello.</p> }
          <form (ngSubmit)="send()">
            <textarea name="text" rows="2" maxlength="1000" aria-label="Write a message (up to 1000 characters)" placeholder="Write a message (up to 1000 characters)" [(ngModel)]="text"></textarea>
            @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
            <button type="submit" class="send-message">Send</button>
          </form>
        } @else {
          <p>Choose a conversation.</p>
        }
      </section>
    </div>
  `,
  styles: `.layout { display: flex; gap: 1.5rem; flex-wrap: wrap; } nav { flex: 0 0 13rem; } .conv { display: block; width: 100%; text-align: left; margin: .25rem 0; border-radius: 10px; } .conv.active { background: var(--orange-tint); border-color: var(--orange); color: #000; font-weight: 700; } .msg { background: var(--white); border: 1px solid var(--line); border-radius: 12px; padding: .4rem .75rem; margin: .35rem 0; max-width: 85%; } .msg.mine { margin-left: auto; background: var(--orange-tint); border-color: var(--orange); } textarea { width: 100%; max-width: 32rem; display: block; } .error { color: #b00020; }`,
})
export class MessagingHome implements OnInit {
  private readonly api = inject(MessagingService);
  readonly conversations = signal<ConversationSummary[]>([]);
  readonly messages = signal<ChatMessage[]>([]);
  readonly currentId = signal<number | null>(null);
  readonly currentName = signal('');
  readonly error = signal('');
  text = '';

  ngOnInit(): void {
    this.refresh();
  }
  refresh(): void {
    this.api.conversations().subscribe((c) => this.conversations.set(c));
  }
  open(c: ConversationSummary): void {
    this.api.open(c.connectionId).subscribe((conv) => {
      if (!conv) return;
      this.currentId.set(c.connectionId);
      this.currentName.set(c.other.displayName);
      this.messages.set(conv.messages ?? []);
      this.refresh(); // opening clears the unread count (FR-052)
    });
  }
  send(): void {
    const id = this.currentId();
    if (!id) return;
    this.api.send(id, this.text).subscribe((r) => {
      this.error.set(r.ok ? '' : (r.errors?.['text'] ?? r.message ?? 'Message not sent.'));
      if (r.ok) {
        this.text = '';
        this.api.open(id).subscribe((conv) => this.messages.set(conv?.messages ?? []));
        this.refresh();
      }
    });
  }
}
