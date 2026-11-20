import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Avatar } from '../shared/avatar';
import { Post } from './communities.service';

/** One card per post, shared by the feed, search results and community page. Each card names its community. */
@Component({
  selector: 'app-post-list',
  imports: [RouterLink, Avatar],
  template: `
    @for (p of posts(); track p.id) {
      <article class="post">
        @if (showCommunity() && p.community) {
          <div><a class="community-tag" [routerLink]="['/communities', p.communityId]" [attr.aria-label]="'Community: ' + p.community">{{ p.community }}</a></div>
        }
        <div class="byline">
          <app-avatar [name]="p.author.displayName" [size]="1.5" />
          <span>{{ p.author.displayName }} · {{ p.createdAt.slice(0, 16).replace('T', ' ') }}@if (p.edited) { · edited }</span>
        </div>
        <a class="title" [routerLink]="['/communities/post', p.id]">{{ p.title }}</a>
        <div><span class="kind" [class.kind-partner]="p.kind === 'study partner request'">{{ p.kind }}</span></div>
        @if (p.notice) { <p class="notice">{{ p.notice }}</p> }
      </article>
    }
  `,
})
export class PostList {
  readonly posts = input.required<Post[]>();
  /** Off on a community's own page, where every post is from the same community. */
  readonly showCommunity = input(true);
}
