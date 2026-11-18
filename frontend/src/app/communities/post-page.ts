import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ConnectionsService } from '../connections/connections.service';
import { CommunitiesService, Post } from './communities.service';

@Component({
  selector: 'app-post-page',
  imports: [FormsModule, RouterLink],
  template: `
    <p><a routerLink="/communities">← Communities</a></p>
    @if (post(); as p) {
      <h2>{{ p.title }}</h2>
      <small>{{ p.kind }} · {{ p.author.displayName }} · {{ p.createdAt.slice(0, 16).replace('T', ' ') }}@if (p.edited) { · edited }</small>
      @if (p.notice) { <p class="notice">{{ p.notice }}</p> }
      <p>{{ p.text }}</p>
      <div class="actions">
        @if (p.mine) { <button type="button" class="delete" (click)="deletePost()">Delete</button> }
        @else { <button type="button" class="connect" (click)="connect(p.author.id)">Send connection request to {{ p.author.displayName }}</button> }
      </div>

      <h3>Replies</h3>
      @for (r of p.replies; track r.id) {
        <div class="reply">
          <strong>{{ r.author.displayName }}</strong>: {{ r.text }} @if (r.edited) { <small>(edited)</small> }
          @if (r.notice) { <small class="notice">{{ r.notice }}</small> }
          @if (r.mine) { <button type="button" (click)="deleteReply(r.id)">Delete</button> }
          @else { <button type="button" (click)="connect(r.author.id)">Connect</button> }
        </div>
      } @empty { <p>No replies yet.</p> }

      <form (ngSubmit)="reply()">
        <textarea name="reply" rows="3" maxlength="1000" placeholder="Write a reply (up to 1000 characters)" [(ngModel)]="text"></textarea>
        @if (error()) { <p class="error">{{ error() }}</p> }
        <button type="submit" class="send-reply">Reply</button>
      </form>
      @if (info()) { <p class="notice">{{ info() }}</p> }
    } @else {
      <p>This post is not available.</p>
    }
  `,
  styles: `textarea { display: block; width: 100%; max-width: 40rem; margin: .4rem 0; } .reply { margin: .4rem 0; } .error { color: #b00020; }`,
})
export class PostPage implements OnInit {
  private readonly api = inject(CommunitiesService);
  private readonly connections = inject(ConnectionsService);
  private readonly route = inject(ActivatedRoute);
  private readonly router = inject(Router);
  private id = 0;
  text = '';
  readonly post = signal<Post | null>(null);
  readonly error = signal('');
  readonly info = signal('');

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }
  load(): void {
    this.api.post(this.id).subscribe({ next: (p) => this.post.set(p), error: () => this.post.set(null) });
  }
  reply(): void {
    this.api.reply(this.id, this.text).subscribe((r) => {
      this.error.set(r.errors ? Object.values(r.errors).join(' ') : '');
      if (r.ok) {
        this.text = '';
        this.load();
      }
    });
  }
  deleteReply(id: number): void {
    this.api.deleteReply(id).subscribe(() => this.load());
  }
  deletePost(): void {
    this.api.deletePost(this.id).subscribe(() => this.router.navigateByUrl('/communities'));
  }
  /** FR-038: send a connection request to the author of a post or reply. The backend applies the rules (FR-043). */
  connect(authorId: number): void {
    this.connections.sendRequest(authorId, '').subscribe((r) => this.info.set(r.ok ? 'Connection request sent.' : (r.message ?? '')));
  }
}
