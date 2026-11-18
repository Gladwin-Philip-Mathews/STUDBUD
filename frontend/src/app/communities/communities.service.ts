import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface Community {
  id: number;
  name: string;
  kind: string;
  memberCount: number;
  joined: boolean;
  notice: string | null;
}
export interface Author {
  id: number;
  displayName: string;
}
export interface Reply {
  id: number;
  postId: number;
  text: string;
  status: string;
  createdAt: string;
  edited: boolean;
  author: Author;
  mine: boolean;
  notice?: string;
}
export interface Post {
  id: number;
  communityId: number;
  kind: string;
  title: string;
  text: string;
  status: string;
  createdAt: string;
  edited: boolean;
  author: Author;
  mine: boolean;
  notice?: string;
  replies?: Reply[];
}
export interface PostPage {
  posts: Post[];
  hasMore: boolean;
  message: string | null;
}
export interface Outcome<T = unknown> {
  ok: boolean;
  item?: T;
  errors?: Record<string, string>;
  message?: string;
}

export const POST_KINDS = ['question', 'share', 'study partner request'];

function failed<T>(e: HttpErrorResponse): Outcome<T> {
  return { ok: false, errors: e.error?.errors, message: e.error?.message ?? 'Something went wrong.' };
}

@Injectable({ providedIn: 'root' })
export class CommunitiesService {
  private readonly http = inject(HttpClient);

  communities(q = ''): Observable<Community[]> {
    return this.http.get<{ communities: Community[] }>('/api/communities', { params: { q } }).pipe(map((r) => r.communities));
  }
  join(id: number): Observable<Outcome> {
    return this.http.post(`/api/communities/${id}/join`, {}).pipe(map(() => ({ ok: true })), catchError((e) => of(failed(e))));
  }
  leave(id: number): Observable<Outcome> {
    return this.http.post(`/api/communities/${id}/leave`, {}).pipe(map(() => ({ ok: true })), catchError((e) => of(failed(e))));
  }
  feed(kind = '', page = 1): Observable<PostPage> {
    return this.http.get<PostPage>('/api/feed', { params: { kind, page } });
  }
  search(q: string, kind = ''): Observable<Outcome<PostPage>> {
    return this.http.get<PostPage>('/api/search', { params: { q, kind } }).pipe(
      map((r) => ({ ok: true, item: r })),
      catchError((e) => of(failed<PostPage>(e)))
    );
  }
  communityPosts(id: number, kind = '', page = 1): Observable<PostPage> {
    return this.http.get<PostPage>(`/api/communities/${id}/posts`, { params: { kind, page } });
  }
  createPost(communityId: number, body: { kind: string; title: string; text: string }): Observable<Outcome<Post>> {
    return this.http.post<{ post: Post }>(`/api/communities/${communityId}/posts`, body).pipe(
      map((r) => ({ ok: true, item: r.post })),
      catchError((e) => of(failed<Post>(e)))
    );
  }
  post(id: number): Observable<Post> {
    return this.http.get<{ post: Post }>(`/api/posts/${id}`).pipe(map((r) => r.post));
  }
  reply(postId: number, text: string): Observable<Outcome<Reply>> {
    return this.http.post<{ reply: Reply }>(`/api/posts/${postId}/replies`, { text }).pipe(
      map((r) => ({ ok: true, item: r.reply })),
      catchError((e) => of(failed<Reply>(e)))
    );
  }
  deletePost(id: number): Observable<Outcome> {
    return this.http.delete(`/api/posts/${id}`).pipe(map(() => ({ ok: true })), catchError((e) => of(failed(e))));
  }
  deleteReply(id: number): Observable<Outcome> {
    return this.http.delete(`/api/replies/${id}`).pipe(map(() => ({ ok: true })), catchError((e) => of(failed(e))));
  }
}
