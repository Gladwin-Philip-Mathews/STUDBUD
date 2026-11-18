import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of, tap } from 'rxjs';
import { AuthService } from '../auth/auth.service';

export interface Profile {
  intent: string;
  cohort: string;
  yearOfStudy: number | null;
  interests: string[];
  courses: string[];
}
export interface CourseOption {
  code: string;
  name: string;
}
export interface SaveResult {
  ok: boolean;
  errors?: Record<string, string>;
  message?: string;
}

export const INTENTS = ['friendship', 'study partner', 'both'];
export const COHORTS = ['first year', 'international', 'both', 'neither', 'prefer not to say'];

@Injectable({ providedIn: 'root' })
export class ProfilesService {
  private readonly http = inject(HttpClient);
  private readonly auth = inject(AuthService);

  load(): Observable<Profile | null> {
    return this.http.get<{ profile: Profile | null }>('/api/profile').pipe(map((r) => r.profile));
  }

  save(profile: Profile): Observable<SaveResult> {
    return this.http.put('/api/profile', profile).pipe(
      tap(() => this.auth.profileComplete.set(true)),
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of({ ok: false, errors: e.error?.errors, message: e.error?.message }))
    );
  }

  searchCourses(query: string): Observable<CourseOption[]> {
    return this.http.get<{ courses: CourseOption[] }>('/api/profile/courses', { params: { q: query } }).pipe(map((r) => r.courses));
  }

  deleteAccount(password: string): Observable<SaveResult> {
    return this.http.request('DELETE', '/api/profile', { body: { password } }).pipe(
      tap(() => this.auth.account.set(null)),
      map(() => ({ ok: true })),
      catchError((e: HttpErrorResponse) => of({ ok: false, message: e.error?.message ?? 'Could not delete the account.' }))
    );
  }
}
