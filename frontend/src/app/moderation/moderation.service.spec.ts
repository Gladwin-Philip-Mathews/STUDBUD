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

  it('returns the named problem when a decision is incomplete (FR-064)', () => {
    let errors: Record<string, string> | undefined;
    svc.decide(3, 'upheld', 'warning', '').subscribe((r) => (errors = r.errors));
    http.expectOne('/api/moderation/reports/3/decision').flush({ errors: { note: 'Write a note.' } }, { status: 400, statusText: 'Bad Request' });
    expect(errors?.['note']).toBeTruthy();
  });
});
