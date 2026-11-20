import { AfterViewChecked, Component, ElementRef, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ReportForm } from '../moderation/report-form';
import { Avatar } from '../shared/avatar';
import { ChatMessage, ConversationSummary, MessagingService } from './messaging.service';

@Component({
  selector: 'app-messaging-home',
  imports: [FormsModule, ReportForm, Avatar],
  template: `
    <div class="page-head">
      <h2>Messages</h2>
      <p class="lead">Private chats with students you are connected to.</p>
    </div>
    <div class="chat-shell">
      <nav class="people" aria-label="Conversations">
        @for (c of conversations(); track c.connectionId) {
          <button type="button" class="conv" [class.active]="c.connectionId === currentId()" [attr.aria-current]="c.connectionId === currentId() ? 'true' : null" (click)="open(c)">
            <app-avatar [name]="c.other.displayName" [size]="2.5" />
            <span class="name">{{ c.other.displayName }}</span>
            @if (c.unread) { <span class="badge">{{ c.unread }}</span> }
          </button>
        } @empty { <p class="hint pad">No connections yet. Accept or send a connection request first.</p> }
      </nav>

      <section class="chat" aria-label="Conversation">
        @if (currentId()) {
          <header class="chat-head">
            <app-avatar [name]="currentName()" [size]="2.75" />
            <div>
              <strong class="chat-name" id="chat-name">{{ currentName() }}</strong>
              <small>You are messaging {{ currentName() }}</small>
            </div>
          </header>
          <div class="thread" #thread aria-live="polite">
            @for (m of messages(); track m.id) {
              <div class="bubble-row" [class.mine]="m.mine">
                <div class="bubble" [class.mine]="m.mine">
                  <span class="who">{{ m.mine ? 'You' : currentName() }}</span>
                  <span class="text">{{ m.text }}</span>
                  <small class="time">{{ m.sentAt.slice(11, 16) }}</small>
                  @if (m.notice) { <small class="notice">{{ m.notice }}</small> }
                </div>
                @if (!m.mine) { <app-report-form itemType="message" [itemId]="m.id" /> }
              </div>
            } @empty { <p class="empty">No messages yet. Say hello to {{ currentName() }}.</p> }
          </div>
          <form class="composer" (ngSubmit)="send()">
            <textarea name="text" rows="2" maxlength="1000" [attr.aria-label]="'Write a message to ' + currentName() + ' (up to 1000 characters)'" [placeholder]="'Message ' + currentName() + '…'" [(ngModel)]="text" (keydown.enter)="enterToSend($event)"></textarea>
            <button type="submit" class="send-message">Send</button>
          </form>
          @if (error()) { <p class="error pad" role="alert">{{ error() }}</p> }
        } @else {
          <div class="placeholder"><p class="empty">Choose a conversation to start chatting.</p></div>
        }
      </section>
    </div>
  `,
  styles: `
    .chat-shell { display: grid; grid-template-columns: 17rem minmax(0, 1fr); background: var(--white); border: 1px solid var(--line); border-radius: var(--radius-lg); box-shadow: var(--shadow-sm); overflow: hidden; min-height: 30rem; }
    .people { border-right: 1px solid var(--line); padding: .5rem; display: grid; align-content: start; gap: .15rem; background: #fbfaf8; }
    .conv { display: flex; align-items: center; gap: .65rem; width: 100%; text-align: left; border: 0; border-radius: 12px; background: transparent; padding: .55rem .6rem; font-weight: 600; color: var(--ink); }
    .conv:hover { background: var(--paper); color: var(--ink); box-shadow: none; }
    .conv.active { background: var(--orange-tint); box-shadow: inset 3px 0 0 var(--orange); }
    .conv .name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .chat { display: flex; flex-direction: column; min-width: 0; }
    .chat-head { display: flex; align-items: center; gap: .75rem; padding: .75rem 1rem; border-bottom: 1px solid var(--line); background: var(--white); }
    .chat-head div { display: grid; line-height: 1.25; }
    .chat-name { font-size: 1.1rem; }
    .thread { flex: 1; overflow-y: auto; padding: 1rem; display: flex; flex-direction: column; gap: .6rem; max-height: 26rem; min-height: 14rem; background: var(--paper); }
    .bubble-row { display: flex; flex-direction: column; align-items: flex-start; gap: .1rem; }
    .bubble-row.mine { align-items: flex-end; }
    .bubble { max-width: min(30rem, 85%); padding: .5rem .85rem; border-radius: 18px 18px 18px 4px; background: var(--white); border: 1px solid var(--line); display: grid; gap: .1rem; }
    .bubble.mine { border-radius: 18px 18px 4px 18px; background: var(--orange); border-color: var(--orange); color: #000; }
    .bubble .who { font-size: .75rem; font-weight: 700; opacity: .75; }
    .bubble .text { white-space: pre-wrap; overflow-wrap: anywhere; }
    .bubble .time { justify-self: end; color: inherit; opacity: .7; font-size: .72rem; }
    .composer { display: flex; gap: .6rem; align-items: flex-end; padding: .75rem 1rem; border-top: 1px solid var(--line); max-width: none; }
    .composer textarea { flex: 1; resize: none; border-radius: 18px; }
    .placeholder { display: grid; place-items: center; flex: 1; padding: 2rem; }
    .pad { padding: 0 1rem .75rem; }
    @media (max-width: 760px) { .chat-shell { grid-template-columns: 1fr; } .people { border-right: 0; border-bottom: 1px solid var(--line); grid-auto-flow: column; overflow-x: auto; } .conv { width: auto; } }
  `,
})
export class MessagingHome implements OnInit, AfterViewChecked {
  private readonly api = inject(MessagingService);
  @ViewChild('thread') private thread?: ElementRef<HTMLElement>;
  readonly conversations = signal<ConversationSummary[]>([]);
  readonly messages = signal<ChatMessage[]>([]);
  readonly currentId = signal<number | null>(null);
  readonly currentName = signal('');
  readonly error = signal('');
  text = '';
  private scrollDown = false;

  ngOnInit(): void {
    this.refresh();
  }
  ngAfterViewChecked(): void {
    if (this.scrollDown && this.thread) {
      this.thread.nativeElement.scrollTop = this.thread.nativeElement.scrollHeight;
      this.scrollDown = false;
    }
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
      this.error.set('');
      this.scrollDown = true;
      this.refresh(); // opening clears the unread count (FR-052)
    });
  }
  /** Enter sends, Shift+Enter makes a new line. */
  enterToSend(event: Event): void {
    const e = event as KeyboardEvent;
    if (e.shiftKey) return;
    e.preventDefault();
    this.send();
  }
  send(): void {
    const id = this.currentId();
    if (!id) return;
    this.api.send(id, this.text).subscribe((r) => {
      this.error.set(r.ok ? '' : (r.errors?.['text'] ?? r.message ?? 'Message not sent.'));
      if (r.ok) {
        this.text = '';
        this.api.open(id).subscribe((conv) => {
          this.messages.set(conv?.messages ?? []);
          this.scrollDown = true;
        });
        this.refresh();
      }
    });
  }
}
