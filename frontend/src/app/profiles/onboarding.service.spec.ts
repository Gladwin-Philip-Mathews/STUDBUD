import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { OnboardingService } from './onboarding.service';

describe('OnboardingService', () => {
  let svc: OnboardingService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(OnboardingService);
    http = TestBed.inject(HttpTestingController);
  });

  it('returns no question when the student has nothing due', () => {
    let q: unknown = 'unset';
    svc.question().subscribe((r) => (q = r));
    http.expectOne('/api/onboarding/question').flush({ question: null });
    expect(q).toBeNull();
  });

  it('sends "skipped" when the student skips (FR-090)', () => {
    svc.answer('skipped').subscribe();
    const req = http.expectOne('/api/onboarding/answer');
    expect(req.request.body).toEqual({ answer: 'skipped' });
    req.flush({});
  });
});
