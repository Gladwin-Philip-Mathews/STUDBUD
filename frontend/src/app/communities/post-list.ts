import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Post } from './communities.service';

/** One card per post, shared by the feed, search results and community page. */
@Component({
  selector: 'app-post-list',
  imports: [RouterLink],
  template: `
    @for (p of posts(); track p.id) {
      <article class="post">
        <a class="title" [routerLink]="['/communities/post', p.id]">{{ p.title }}</a>
        <span class="meta">
          <span class="kind" [class.kind-partner]="p.kind === 'study partner request'">{{ p.kind }}</span>
          {{ p.author.displayName }} · {{ p.createdAt.slice(0, 16).replace('T', ' ') }}@if (p.edited) { · edited }
        </span>
        @if (p.notice) { <p class="notice">{{ p.notice }}</p> }
      </article>
    }
  `,
})
export class PostList {
  readonly posts = input.required<Post[]>();
}
