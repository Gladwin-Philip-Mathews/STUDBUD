import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { Community, CommunitiesService, POST_KINDS, Post } from './communities.service';
import { PostList } from './post-list';
import { Section, Sections } from '../shared/sections';

@Component({
  selector: 'app-communities-home',
  imports: [FormsModule, RouterLink, PostList, Sections],
  template: `
    <div class="page-head">
      <h2>Communities</h2>
      <p class="lead">Your feed and the communities you can join.</p>
    </div>
    <app-sections [sections]="sectionList()" [(active)]="section" label="Communities sections">
      @if (section() === 'feed') {
        <div class="feed-layout">
          <div>
            <div class="bar">
              <input name="search" type="search" aria-label="Search posts in your communities" placeholder="Search posts" [(ngModel)]="query" (keydown.enter)="search()" />
              <button type="button" (click)="search()">Search</button>
              <select name="kind" aria-label="Show posts of one kind" [(ngModel)]="kind" (ngModelChange)="load()">
                <option value="">All kinds</option>
                @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
              </select>
            </div>
            @if (searchError()) { <p class="error">{{ searchError() }}</p> }
            <app-post-list [posts]="posts()" />
            @if (message()) { <p class="empty" id="feed-message">{{ message() }}</p> }
            @if (hasMore()) { <button type="button" (click)="more()">Show more</button> }
          </div>
          <aside class="card mine" aria-label="Your communities">
            <h3>Your communities</h3>
            @for (c of joined(); track c.id) {
              <a [routerLink]="['/communities', c.id]" class="mine-link"><span>{{ c.name }}</span><small>{{ c.memberCount }}</small></a>
            } @empty { <p class="hint">You have not joined any yet. Open "Browse communities".</p> }
          </aside>
        </div>
      }

      @if (section() === 'browse') {
        <input name="communityQuery" type="search" aria-label="Find a community" placeholder="Find a community" [(ngModel)]="communityQuery" (ngModelChange)="loadCommunities()" />
        <p class="hint">Can't find yours? Ask the admin, or <a routerLink="/profiles" [queryParams]="{ section: 'interests' }">suggest an interest on your profile</a>.</p>
        <div class="grid">
          @for (c of communities(); track c.id) {
            <div class="card community">
              <div>
                @if (c.joined) { <a [routerLink]="['/communities', c.id]"><strong>{{ c.name }}</strong></a> } @else { <strong>{{ c.name }}</strong> }
                <div class="meta"><span class="kind">{{ c.kind }}</span> <small>{{ c.memberCount }} members</small></div>
                @if (c.notice) { <small class="notice">{{ c.notice }}</small> }
              </div>
              @if (c.joined) { <button type="button" class="btn-small" (click)="leave(c)">Leave</button> }
              @else { <button type="button" class="btn-small primary" (click)="join(c)">Join</button> }
            </div>
          } @empty { <p class="empty">No communities found.</p> }
        </div>
        @if (joinError()) { <p class="error">{{ joinError() }}</p> }
      }
    </app-sections>
  `,
  styles: `
    .feed-layout { display: grid; grid-template-columns: minmax(0, 1fr) 14rem; gap: 1.25rem; align-items: start; }
    .mine { margin-top: 0; position: sticky; top: 1rem; padding: 1rem; }
    .mine-link { display: flex; justify-content: space-between; gap: .5rem; padding: .4rem .5rem; border-radius: 8px; color: var(--ink); text-decoration: none; font-weight: 600; }
    .mine-link:hover { background: var(--orange-tint); }
    .community { display: flex; justify-content: space-between; gap: .75rem; align-items: flex-start; margin: 0; }
    .meta { display: flex; gap: .5rem; align-items: center; margin: .3rem 0; }
    @media (max-width: 900px) { .feed-layout { grid-template-columns: 1fr; } .mine { position: static; } }
  `,
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
  readonly section = signal('feed');
  readonly joined = computed(() => this.communities().filter((c) => c.joined));
  readonly sectionList = computed<Section[]>(() => [
    { id: 'feed', label: 'Your feed' },
    { id: 'browse', label: 'Browse communities' },
  ]);

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
