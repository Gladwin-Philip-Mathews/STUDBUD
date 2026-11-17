import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { NotificationsService } from './notifications.service';

describe('NotificationsService', () => {
  let api: NotificationsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(NotificationsService);
    http = TestBed.inject(HttpTestingController);
  });

  it('keeps the unread count for every page', () => {
    api.refresh();
    http.expectOne('/api/notifications/unread-count').flush({ unread: 3 });
    expect(api.unread()).toBe(3);
  });

  it('refreshes the count after marking one as read', () => {
    api.markRead(7).subscribe();
    http.expectOne('/api/notifications/7/read').flush({});
    http.expectOne('/api/notifications/unread-count').flush({ unread: 0 });
    expect(api.unread()).toBe(0);
  });

  it('shows 0 when the backend cannot be reached', () => {
    api.refresh();
    http.expectOne('/api/notifications/unread-count').flush({}, { status: 401, statusText: 'No' });
    expect(api.unread()).toBe(0);
  });
});
