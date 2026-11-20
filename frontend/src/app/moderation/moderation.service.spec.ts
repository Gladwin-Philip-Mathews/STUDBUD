import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ModerationService } from './moderation.service';

describe('ModerationService', () => {
  let svc: ModerationService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(ModerationService);
    http = TestBed.inject(HttpTestingController);
  });

  it('sends the item type, id and reason of a report (FR-060)', () => {
    svc.report('post', 7, 'spam', '').subscribe();
    const req = http.expectOne('/api/reports');
    expect(req.request.body).toEqual({ itemType: 'post', itemId: 7, reason: 'spam', text: '' });
    req.flush({ message: 'Thank you.' });
  });

  it('sends the escalation choice with an upheld decision and returns the case summary (DF-23, DF-24)', () => {
    let data: Record<string, unknown> | undefined;
    svc.decide(3, 'upheld', 'warning', 'Reviewed.', true).subscribe((r) => (data = r.data));
    const req = http.expectOne('/api/moderation/reports/3/decision');
    expect(req.request.body).toEqual({ decision: 'upheld', action: 'warning', note: 'Reviewed.', escalate: true });
    req.flush({ message: 'Decision recorded.', caseSummary: { reportId: 3, decision: 'upheld' } });
    expect(data?.['reportId']).toBe(3);
  });

  it('records a later note on a closed report (DF-25, FR-067)', () => {
    let ok = false;
    svc.addNote(3, 'Student Affairs confirmed the warning.').subscribe((r) => (ok = r.ok));
    const req = http.expectOne('/api/moderation/reports/3/notes');
    expect(req.request.body).toEqual({ note: 'Student Affairs confirmed the warning.' });
    req.flush({ message: 'Note added.' }, { status: 201, statusText: 'Created' });
    expect(ok).toBeTrue();
  });

  it('returns the named problem when a decision is incomplete (FR-064)', () => {
    let errors: Record<string, string> | undefined;
    svc.decide(3, 'upheld', 'warning', '').subscribe((r) => (errors = r.errors));
    http.expectOne('/api/moderation/reports/3/decision').flush({ errors: { note: 'Write a note.' } }, { status: 400, statusText: 'Bad Request' });
    expect(errors?.['note']).toBeTruthy();
  });

  it('loads the reported post, its thread and the student history for a moderator (FR-064)', () => {
    let title = '';
    svc.context(4).subscribe((c) => (title = c?.thread?.post.title ?? ''));
    http.expectOne('/api/moderation/reports/4/context').flush({ context: { reportId: 4, reportedStudent: 'Bo', history: [],
      thread: { post: { id: 1, community: 'SWEN-261', kind: 'share', title: 'A post', text: 't', status: 'visible', author: 'Bo', createdAt: '2026-11-20T10:00', edited: false, reported: true }, replies: [] } } });
    expect(title).toBe('A post');
  });
});
