import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface CourseRow { code: string; title: string; status: string }
export interface DomainRow { domain: string; addedAt: string | null }
export interface SettingRow { name: string; value: number; unit: string }
export interface Status { accounts: number; activeUsers: number; posts: number; openReports: number; failedEmails: number }
export interface GroupRow {
  cohort: string;
  students: number;
  requests_sent: number;
  accepted_within_7_days_pct: number | null;
  safety_reports: number;
  acknowledged_within_48h_pct: number | null;
  upheld_reports: number;
  active_users: number;
  upheld_per_100_active: number | null;
  answered_both: number;
  contact_increased: number;
}
export interface PilotReport {
  groups: GroupRow[];
  weekly: { week: number; requestsSent: number; acceptedWithin7DaysPct: number | null; safetyReports: number }[];
  pilotWeek: number;
  period: { from: string; to: string };
  records: number;
}
export interface Done {
  ok: boolean;
  message?: string;
}

function done(e: HttpErrorResponse): Done {
  return { ok: false, message: Object.values(e.error?.errors ?? {}).join(' ') || e.error?.message || 'That did not work.' };
}

@Injectable({ providedIn: 'root' })
export class AdminService {
  private readonly http = inject(HttpClient);

  private post(url: string, body: unknown = {}): Observable<Done> {
    return this.http.post<{ message?: string }>(url, body).pipe(map((r) => ({ ok: true, message: r?.message })), catchError((e) => of(done(e))));
  }

  status(): Observable<Status> {
    return this.http.get<{ status: Status }>('/api/admin/status').pipe(map((r) => r.status));
  }
  courses(): Observable<CourseRow[]> {
    return this.http.get<{ courses: CourseRow[] }>('/api/admin/courses').pipe(map((r) => r.courses));
  }
  addCourse(code: string, title: string): Observable<Done> {
    return this.post('/api/admin/courses', { code, title });
  }
  archiveCourse(code: string): Observable<Done> {
    return this.post(`/api/admin/courses/${encodeURIComponent(code)}/archive`);
  }
  importCourses(csv: string): Observable<Done> {
    return this.post('/api/admin/courses/import', { csv });
  }
  domains(): Observable<DomainRow[]> {
    return this.http.get<{ domains: DomainRow[] }>('/api/admin/domains').pipe(map((r) => r.domains));
  }
  addDomain(domain: string): Observable<Done> {
    return this.post('/api/admin/domains', { domain });
  }
  removeDomain(domain: string): Observable<Done> {
    return this.http.delete(`/api/admin/domains/${encodeURIComponent(domain)}`).pipe(map(() => ({ ok: true })), catchError((e) => of(done(e))));
  }
  createCommunity(name: string): Observable<Done> {
    return this.post('/api/admin/communities', { name });
  }
  setModerator(email: string, enable: boolean): Observable<Done> {
    return this.post('/api/admin/moderators', { email, enable });
  }
  moderators(): Observable<{ id: number; email: string; displayName: string }[]> {
    return this.http.get<{ moderators: { id: number; email: string; displayName: string }[] }>('/api/admin/moderators').pipe(map((r) => r.moderators));
  }
  settings(): Observable<SettingRow[]> {
    return this.http.get<{ settings: SettingRow[] }>('/api/admin/settings').pipe(map((r) => r.settings));
  }
  updateSetting(name: string, value: number): Observable<Done> {
    return this.http.put(`/api/admin/settings/${name}`, { value }).pipe(map(() => ({ ok: true, message: 'Saved.' })), catchError((e) => of(done(e))));
  }
  pilotReport(): Observable<PilotReport> {
    return this.http.get<PilotReport>('/api/admin/pilot-report');
  }
}
