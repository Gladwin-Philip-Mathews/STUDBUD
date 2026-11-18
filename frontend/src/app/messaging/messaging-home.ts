import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ChatMessage, ConversationSummary, MessagingService } from './messaging.service';

@Component({
  selector: 'app-messaging-home',
  imports: [FormsModule],
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
            </p>
          } @empty { <p>No messages yet. Say hello.</p> }
          <form (ngSubmit)="send()">
            <textarea name="text" rows="2" maxlength="1000" placeholder="Write a message (up to 1000 characters)" [(ngModel)]="text"></textarea>
            @if (error()) { <p class="error">{{ error() }}</p> }
            <button type="submit" class="send-message">Send</button>
          </form>
        } @else {
          <p>Choose a conversation.</p>
        }
      </section>
    </div>
  `,
  styles: `.layout { display: flex; gap: 1.5rem; } nav { min-width: 12rem; } .conv { display: block; width: 100%; text-align: left; margin: .2rem 0; } .active { font-weight: bold; } .badge { background: #b00020; color: #fff; border-radius: 1rem; padding: 0 .45rem; } .mine { text-align: right; } textarea { width: 100%; max-width: 32rem; display: block; } .error { color: #b00020; }`,
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
