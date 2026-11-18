import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Community, CommunitiesService, POST_KINDS, Post } from './communities.service';
import { PostList } from './post-list';

@Component({
  selector: 'app-communities-home',
  imports: [FormsModule, RouterLink, PostList],
  template: `
    <h2>Communities</h2>

    <h3>Your feed</h3>
    <div class="bar">
      <input name="search" placeholder="Search posts in your communities" [(ngModel)]="query" (keydown.enter)="search()" />
      <button type="button" (click)="search()">Search</button>
      <select name="kind" [(ngModel)]="kind" (ngModelChange)="load()">
        <option value="">All kinds</option>
        @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
      </select>
    </div>
    @if (searchError()) { <p class="error">{{ searchError() }}</p> }
    <app-post-list [posts]="posts()" />
    @if (message()) { <p id="feed-message">{{ message() }}</p> }
    @if (hasMore()) { <button type="button" (click)="more()">Show more</button> }

    <h3>All communities</h3>
    <input name="communityQuery" placeholder="Find a community" [(ngModel)]="communityQuery" (ngModelChange)="loadCommunities()" />
    @for (c of communities(); track c.id) {
      <div class="row">
        <span>
          @if (c.joined) { <a [routerLink]="['/communities', c.id]"><strong>{{ c.name }}</strong></a> } @else { <strong>{{ c.name }}</strong> }
          <small> {{ c.kind }} · {{ c.memberCount }} members</small>
          @if (c.notice) { <small class="notice"><br />{{ c.notice }}</small> }
        </span>
        @if (c.joined) { <button type="button" (click)="leave(c)">Leave</button> }
        @else { <button type="button" (click)="join(c)">Join</button> }
      </div>
    } @empty { <p>No communities found.</p> }
    @if (joinError()) { <p class="error">{{ joinError() }}</p> }
  `,
  styles: `.row { display: flex; gap: .5rem; align-items: center; margin: .35rem 0; } .row span { flex: 1; } .bar { display: flex; gap: .5rem; flex-wrap: wrap; } .error { color: #b00020; }`,
})
export class CommunitiesHome implements OnInit {
  private readonly api = inject(CommunitiesService);
  readonly kinds = POST_KINDS;
  kind = '';
  query = '';
  communityQuery = '';
  private page = 1;
  readonly posts = signal<Post[]>([]);
  readonly communities = signal<Community[]>([]);
  readonly message = signal<string | null>(null);
  readonly hasMore = signal(false);
  readonly searchError = signal('');
  readonly joinError = signal('');

  ngOnInit(): void {
    this.load();
    this.loadCommunities();
  }

  load(): void {
    this.page = 1;
    this.searchError.set('');
    this.api.feed(this.kind, 1).subscribe((r) => this.show(r.posts, r.hasMore, r.message));
  }
  more(): void {
    this.page += 1;
    this.api.feed(this.kind, this.page).subscribe((r) => this.show([...this.posts(), ...r.posts], r.hasMore, r.message));
  }
  search(): void {
    if (!this.query.trim()) return this.load();
    this.api.search(this.query, this.kind).subscribe((r) => {
      this.searchError.set(r.ok ? '' : (r.message ?? ''));
      if (r.ok && r.item) this.show(r.item.posts, r.item.hasMore, r.item.message);
    });
  }
  private show(posts: Post[], more: boolean, message: string | null): void {
    this.posts.set(posts);
    this.hasMore.set(more);
    this.message.set(message);
  }

  loadCommunities(): void {
    this.api.communities(this.communityQuery).subscribe((c) => this.communities.set(c));
  }
  join(c: Community): void {
    this.api.join(c.id).subscribe((r) => {
      this.joinError.set(r.ok ? '' : (r.message ?? ''));
      this.loadCommunities();
      this.load();
    });
  }
  leave(c: Community): void {
    this.api.leave(c.id).subscribe(() => {
      this.loadCommunities();
      this.load();
    });
  }
}
