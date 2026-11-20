import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AdminService } from './admin.service';

describe('AdminService', () => {
  let svc: AdminService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(AdminService);
    http = TestBed.inject(HttpTestingController);
  });

  it('shows the duplicate code message when a course is refused (FR-100)', () => {
    let message = '';
    svc.addCourse('SWEN-261', 'x').subscribe((r) => (message = r.message ?? ''));
    http.expectOne('/api/admin/courses').flush({ errors: { code: 'This course code is already on the list.' } }, { status: 400, statusText: 'Bad Request' });
    expect(message).toContain('already on the list');
  });

  it('saves a setting by name (FR-104)', () => {
    svc.updateSetting('OVERDUE_FLAG', 24).subscribe();
    const req = http.expectOne('/api/admin/settings/OVERDUE_FLAG');
    expect(req.request.body).toEqual({ value: 24 });
    req.flush({ settings: [] });
  });

  it('lists the suggestions and creates a community from one', () => {
    let names: string[] = [];
    svc.suggestions().subscribe((r) => (names = r.map((x) => x.name)));
    http.expectOne('/api/admin/interest-suggestions').flush({ suggestions: [{ id: 3, name: 'Movies', suggestedByName: 'Omar', suggestedAt: '' }] });
    expect(names).toEqual(['Movies']);
    svc.createFromSuggestion(3).subscribe();
    http.expectOne('/api/admin/interest-suggestions/3/create').flush({ community: { id: 9, name: 'Movies' } }, { status: 201, statusText: 'Created' });
  });
});
