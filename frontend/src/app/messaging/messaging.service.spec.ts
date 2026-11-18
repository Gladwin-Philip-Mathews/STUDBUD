import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { MessagingService } from './messaging.service';

describe('MessagingService', () => {
  let svc: MessagingService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(MessagingService);
    http = TestBed.inject(HttpTestingController);
  });

  it('shows the plain refusal when the connection is not accepted (FR-051)', () => {
    let result: { ok: boolean; message?: string } | undefined;
    svc.send(5, 'hi').subscribe((r) => (result = r));
    http.expectOne('/api/messages/conversations/5').flush({ message: 'You can only message students you are connected with.' }, { status: 403, statusText: 'Forbidden' });
    expect(result?.ok).toBe(false);
    expect(result?.message).toContain('connected');
  });

  it('returns null when a conversation cannot be opened', () => {
    let result: unknown = 'unset';
    svc.open(9).subscribe((r) => (result = r));
    http.expectOne('/api/messages/conversations/9').flush({}, { status: 403, statusText: 'Forbidden' });
    expect(result).toBeNull();
  });
});
