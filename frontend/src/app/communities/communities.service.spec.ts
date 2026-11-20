import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { CommunitiesService } from './communities.service';

describe('CommunitiesService', () => {
  let svc: CommunitiesService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(CommunitiesService);
    http = TestBed.inject(HttpTestingController);
  });

  it('returns each named problem when a post is refused (FR-031)', () => {
    let errors: Record<string, string> | undefined;
    svc.createPost(1, { kind: '', title: 'abc', text: '' }).subscribe((r) => (errors = r.errors));
    http.expectOne('/api/communities/1/posts').flush({ errors: { kind: 'k', title: 't', text: 'x' } }, { status: 400, statusText: 'Bad Request' });
    expect(Object.keys(errors ?? {})).toEqual(['kind', 'title', 'text']);
  });

  it('asks the feed for one kind at a time (FR-037)', () => {
    svc.feed('share', 2).subscribe();
    const req = http.expectOne((r) => r.url === '/api/feed');
    expect(req.request.params.get('kind')).toBe('share');
    expect(req.request.params.get('page')).toBe('2');
    req.flush({ posts: [], hasMore: false, message: 'No posts yet.' });
  });

  it('reports a too-short search without throwing (FR-036)', () => {
    let message: string | undefined;
    svc.search('s').subscribe((r) => (message = r.message));
    http.expectOne((r) => r.url === '/api/search').flush({ message: 'Enter at least 2 characters.' }, { status: 400, statusText: 'Bad Request' });
    expect(message).toContain('2 characters');
  });

  it('sends an interest suggestion and returns the refusal when the name already exists', () => {
    let errors: Record<string, string> | undefined;
    svc.suggestInterest('Movies').subscribe((r) => (errors = r.errors));
    const req = http.expectOne('/api/communities/suggestions');
    expect(req.request.body).toEqual({ name: 'Movies' });
    req.flush({ errors: { name: 'This community already exists. Find it under Communities.' } }, { status: 400, statusText: 'Bad Request' });
    expect(errors?.['name']).toContain('already exists');
  });
});
