import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ConnectionsService } from './connections.service';

describe('ConnectionsService', () => {
  let api: ConnectionsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(ConnectionsService);
    http = TestBed.inject(HttpTestingController);
  });

  it('sends a request with the note', () => {
    let result: any;
    api.sendRequest(2, 'hi').subscribe((r) => (result = r));
    const req = http.expectOne('/api/connections/requests');
    expect(req.request.body).toEqual({ receiverId: 2, note: 'hi' });
    req.flush({ connection: {} }, { status: 201, statusText: 'Created' });
    expect(result.ok).toBeTrue();
  });

  it('returns the refusal message without a reason that reveals a decline', () => {
    let result: any;
    api.sendRequest(2, '').subscribe((r) => (result = r));
    http.expectOne('/api/connections/requests').flush(
      { reason: 'RECENTLY_DECLINED', message: 'You cannot send a request to this student right now.' },
      { status: 400, statusText: 'Bad Request' }
    );
    expect(result.ok).toBeFalse();
    expect(result.message).not.toContain('declin');
  });

  it('calls the accept endpoint', () => {
    api.act(5, 'accept').subscribe();
    const req = http.expectOne('/api/connections/5/accept');
    expect(req.request.method).toBe('POST');
    req.flush({});
  });
});
