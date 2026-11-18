import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { CommunitiesService, POST_KINDS, Post } from './communities.service';
import { PostList } from './post-list';

@Component({
  selector: 'app-community-page',
  imports: [FormsModule, RouterLink, PostList],
  template: `
    <p><a routerLink="/communities">← All communities</a></p>
    <h2>Community</h2>
    <form (ngSubmit)="create()">
      <h3>New post</h3>
      <select name="newKind" [(ngModel)]="newKind">
        <option value="">Kind…</option>
        @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
      </select>
      @if (errors()['kind']) { <p class="error">{{ errors()['kind'] }}</p> }
      <input name="title" placeholder="Title (5 to 120 characters)" maxlength="120" [(ngModel)]="title" />
      @if (errors()['title']) { <p class="error">{{ errors()['title'] }}</p> }
      <textarea name="text" rows="4" placeholder="Text (up to 2000 characters)" maxlength="2000" [(ngModel)]="text"></textarea>
      @if (errors()['text']) { <p class="error">{{ errors()['text'] }}</p> }
      @if (errors()['community']) { <p class="error">{{ errors()['community'] }}</p> }
      <button type="submit" class="publish">Post</button>
    </form>

    <h3>Posts</h3>
    <select name="filter" [(ngModel)]="kind" (ngModelChange)="load()">
      <option value="">All kinds</option>
      @for (k of kinds; track k) { <option [value]="k">{{ k }}</option> }
    </select>
    <app-post-list [posts]="posts()" />
    @if (message()) { <p>{{ message() }}</p> }
    @if (hasMore()) { <button type="button" (click)="more()">Show more</button> }
  `,
  styles: `input, textarea, select { display: block; margin: .4rem 0; max-width: 100%; } .error { color: #b00020; }`,
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
