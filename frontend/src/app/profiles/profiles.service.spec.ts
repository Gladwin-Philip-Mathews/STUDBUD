import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { AuthService } from '../auth/auth.service';
import { ProfilesService } from './profiles.service';

describe('ProfilesService', () => {
  let svc: ProfilesService;
  let http: HttpTestingController;
  let auth: AuthService;
  const profile = { intent: 'both', cohort: 'first year', yearOfStudy: null, interests: [], courses: [] };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    svc = TestBed.inject(ProfilesService);
    http = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
  });

  it('marks the profile complete after a successful save (FR-010)', () => {
    let ok = false;
    svc.save(profile).subscribe((r) => (ok = r.ok));
    http.expectOne('/api/profile').flush({ profile });
    expect(ok).toBe(true);
    expect(auth.profileComplete()).toBe(true);
  });

  it('returns the named field errors when the backend refuses (AC-FR-010a)', () => {
    let errors: Record<string, string> | undefined;
    svc.save({ ...profile, intent: '' }).subscribe((r) => (errors = r.errors));
    http.expectOne('/api/profile').flush({ errors: { intent: 'Choose friendship, study partner or both.' } }, { status: 400, statusText: 'Bad Request' });
    expect(errors?.['intent']).toContain('Choose');
    expect(auth.profileComplete()).toBe(false);
  });
});
