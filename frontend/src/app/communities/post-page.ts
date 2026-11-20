import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ConnectionsService } from '../connections/connections.service';
import { ReportForm } from '../moderation/report-form';
import { Avatar } from '../shared/avatar';
import { CommunitiesService, Post } from './communities.service';

@Component({
  selector: 'app-post-page',
  imports: [FormsModule, RouterLink, ReportForm, Avatar],
  template: `
    @if (post(); as p) {
      <a class="back" [routerLink]="['/communities', p.communityId]">← Back to {{ p.community || 'the community' }}</a>
      <article class="card post-full">
        @if (p.community) { <div><a class="community-tag" [routerLink]="['/communities', p.communityId]">{{ p.community }}</a></div> }
        <div class="byline">
          <app-avatar [name]="p.author.displayName" [size]="1.6" />
          <span>{{ p.author.displayName }} · {{ p.createdAt.slice(0, 16).replace('T', ' ') }}@if (p.edited) { · edited }</span>
        </div>
        <h2>{{ p.title }}</h2>
        <div><span class="kind" [class.kind-partner]="p.kind === 'study partner request'">{{ p.kind }}</span></div>
        @if (p.notice) { <p class="notice">{{ p.notice }}</p> }
        <p class="body">{{ p.text }}</p>
      <div class="actions">
        @if (p.mine) { <button type="button" class="delete" (click)="deletePost()">Delete</button> }
        @else {
          <button type="button" class="connect" (click)="connect(p.author.id)">Send connection request to {{ p.author.displayName }}</button>
          <app-report-form itemType="post" [itemId]="p.id" />
        }
      </div>
      </article>

      <h3>Replies</h3>
      @for (r of p.replies; track r.id) {
        <div class="reply">
          <app-avatar [name]="r.author.displayName" [size]="2" />
          <div class="reply-body">
            <strong>{{ r.author.displayName }}</strong> <small>{{ r.createdAt.slice(0, 16).replace('T', ' ') }}@if (r.edited) { · edited }</small>
            <p>{{ r.text }}</p>
            @if (r.notice) { <small class="notice">{{ r.notice }}</small> }
            <div class="actions">
              @if (r.mine) { <button type="button" class="btn-small" (click)="deleteReply(r.id)">Delete</button> }
              @else {
                <button type="button" class="btn-small" (click)="connect(r.author.id)">Connect</button>
                <app-report-form itemType="reply" [itemId]="r.id" />
              }
            </div>
          </div>
        </div>
      } @empty { <p class="empty">No replies yet. Be the first to answer.</p> }

      <form class="card" (ngSubmit)="reply()">
        <textarea name="reply" rows="3" maxlength="1000" aria-label="Write a reply (up to 1000 characters)" placeholder="Write a reply (up to 1000 characters)" [(ngModel)]="text"></textarea>
        @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
        <button type="submit" class="send-reply">Reply</button>
      </form>
      @if (info()) { <p class="notice" role="status">{{ info() }}</p> }
    } @else {
      <p>This post is not available.</p>
    }
  `,
  styles: `.post-full .byline { display: flex; align-items: center; gap: .5rem; flex-wrap: wrap; font-size: .875rem; color: var(--muted); margin-bottom: .5rem; } .post-full h2 { margin-bottom: .5rem; } .body { white-space: pre-wrap; font-size: 1.05rem; margin: .75rem 0 1rem; } .reply { display: flex; gap: .75rem; background: var(--white); border: 1px solid var(--line); border-radius: 14px; padding: .8rem 1rem; margin: .6rem 0; box-shadow: var(--shadow-sm); } .reply-body { flex: 1; min-width: 0; } .reply-body p { margin: .2rem 0 .5rem; white-space: pre-wrap; } form { max-width: none; }`,
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
