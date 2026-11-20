import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommunitiesService, POST_KINDS, Post } from './communities.service';
import { PostList } from './post-list';

@Component({
  selector: 'app-community-page',
  imports: [FormsModule, RouterLink, PostList],
  template: `
    <a class="back" routerLink="/communities">← All communities</a>
    <div class="page-head">
      <h2 id="community-name">{{ name() || 'Community' }}</h2>
      <p class="lead">Posting in <strong>{{ name() || 'this community' }}</strong>. Only members can read and reply.</p>
    </div>
    <form class="card" (ngSubmit)="create()">
      <h3>New post in {{ name() || 'this community' }}</h3>
      <select name="newKind" aria-label="Kind of post" [(ngModel)]="newKind">
        <option value="">Kind…</option>
        @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
      </select>
      @if (errors()['kind']) { <p class="error" role="alert">{{ errors()['kind'] }}</p> }
      <input name="title" aria-label="Title (5 to 120 characters)" placeholder="Title (5 to 120 characters)" maxlength="120" [(ngModel)]="title" />
      @if (errors()['title']) { <p class="error" role="alert">{{ errors()['title'] }}</p> }
      <textarea name="text" rows="4" aria-label="Text (up to 2000 characters)" placeholder="Text (up to 2000 characters)" maxlength="2000" [(ngModel)]="text"></textarea>
      @if (errors()['text']) { <p class="error" role="alert">{{ errors()['text'] }}</p> }
      @if (errors()['community']) { <p class="error" role="alert">{{ errors()['community'] }}</p> }
      <button type="submit" class="publish">Post</button>
    </form>

    <div class="bar head-bar">
      <h3>Posts in {{ name() || 'this community' }}</h3>
      <select name="filter" aria-label="Show posts of one kind" [(ngModel)]="kind" (ngModelChange)="load()">
        <option value="">All kinds</option>
        @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
      </select>
    </div>
    <app-post-list [posts]="posts()" [showCommunity]="false" />
    @if (message()) { <p class="empty" role="status">{{ message() }}</p> }
    @if (hasMore()) { <button type="button" (click)="more()">Show more</button> }
  `,
  styles: `.head-bar { justify-content: space-between; margin-top: 1.5rem; } .head-bar h3 { margin: 0; } .head-bar select { max-width: 12rem; } form { max-width: none; }`,
})
export class CommunityPage implements OnInit {
  private readonly api = inject(CommunitiesService);
  private readonly route = inject(ActivatedRoute);
  readonly kinds = POST_KINDS;
  private id = 0;
  private page = 1;
  kind = '';
  newKind = '';
  title = '';
  text = '';
  readonly posts = signal<Post[]>([]);
  readonly message = signal<string | null>(null);
  readonly hasMore = signal(false);
  readonly errors = signal<Record<string, string>>({});
  readonly name = signal('');

  ngOnInit(): void {
    this.id = Number(this.route.snapshot.paramMap.get('id'));
    this.load();
  }
  load(): void {
    this.page = 1;
    this.api.communityPosts(this.id, this.kind, 1).subscribe({
      next: (r) => {
        this.posts.set(r.posts);
        this.hasMore.set(r.hasMore);
        this.message.set(r.message);
        if (r.community) this.name.set(r.community.name);
      },
      error: () => this.message.set('Join this community to read its posts.'),
    });
  }
  more(): void {
    this.page += 1;
    this.api.communityPosts(this.id, this.kind, this.page).subscribe((r) => {
      this.posts.update((l) => [...l, ...r.posts]);
      this.hasMore.set(r.hasMore);
    });
  }
  create(): void {
    this.api.createPost(this.id, { kind: this.newKind, title: this.title, text: this.text }).subscribe((r) => {
      this.errors.set(r.errors ?? {}); // what the student typed stays in the form (FR-031)
      if (r.ok) {
        this.title = this.text = this.newKind = '';
        this.load();
      }
    });
  }
}
