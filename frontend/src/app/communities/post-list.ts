import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Post } from './communities.service';

/** One line per post, shared by the feed, search results and community page. */
@Component({
  selector: 'app-post-list',
  imports: [RouterLink],
  template: `
    @for (p of posts(); track p.id) {
      <article class="post">
        <a [routerLink]="['/communities/post', p.id]"><strong>{{ p.title }}</strong></a>
        <small> {{ p.kind }} · {{ p.author.displayName }} · {{ p.createdAt.slice(0, 16).replace('T', ' ') }}@if (p.edited) { · edited }</small>
        @if (p.notice) { <p class="notice">{{ p.notice }}</p> }
      </article>
    }
  `,
  styles: `.post { margin: .5rem 0; }`,
})
export class PostList {
  readonly posts = input.required<Post[]>();
}
