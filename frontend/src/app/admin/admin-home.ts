import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Section, Sections } from '../shared/sections';
import { AdminService, CourseRow, DomainRow, PilotReport, SettingRow, Status, SuggestionRow } from './admin.service';

@Component({
  selector: 'app-admin-home',
  imports: [FormsModule, Sections],
  template: `
    <div class="page-head">
      <h2>Administration</h2>
      <p class="lead">Courses, communities, roles, limits and pilot figures.</p>
    </div>
    @if (message()) { <p class="notice" id="admin-message">{{ message() }}</p> }

    <app-sections [sections]="sectionList()" [(active)]="section" label="Administration sections">
      @if (section() === 'status') {
        <h3>System status</h3>
        @if (status(); as s) {
          <div class="stat-grid">
            <div class="stat"><strong>{{ s.accounts }}</strong><span>Accounts</span></div>
            <div class="stat"><strong>{{ s.activeUsers }}</strong><span>Active, last 7 days</span></div>
            <div class="stat"><strong>{{ s.posts }}</strong><span>Posts</span></div>
            <div class="stat"><strong>{{ s.openReports }}</strong><span>Open reports</span></div>
            <div class="stat"><strong>{{ s.failedEmails }}</strong><span>Failed email messages</span></div>
          </div>
        }
      }

      @if (section() === 'courses') {
        <h3>Courses</h3>
        <div class="bar">
          <input name="code" aria-label="Course code" placeholder="Code, e.g. SWEN-261" [(ngModel)]="code" />
          <input name="title" aria-label="Course title" placeholder="Title" [(ngModel)]="title" />
          <button type="button" class="add-course" (click)="addCourse()">Add course</button>
        </div>
        <textarea name="csv" rows="3" aria-label="Course list to import, one course per line as code,title" placeholder="Import: one course per line as code,title" [(ngModel)]="csv"></textarea>
        <p><button type="button" (click)="importCourses()">Import list</button></p>
        @for (c of courses(); track c.code) {
          <div class="row"><span><strong>{{ c.code }}</strong> {{ c.title }} <small>({{ c.status }})</small></span>
            @if (c.status === 'active') { <button type="button" class="btn-small" (click)="archiveCourse(c.code)">Archive</button> }
          </div>
        }
      }

      @if (section() === 'domains') {
        <h3>Accepted email domains</h3>
        <div class="bar">
          <input name="domain" aria-label="Email domain to accept" placeholder="g.rit.edu" [(ngModel)]="domain" />
          <button type="button" (click)="addDomain()">Add domain</button>
        </div>
        @for (d of domains(); track d.domain) {
          <div class="row"><span>{{ d.domain }}</span> <button type="button" class="btn-small" (click)="removeDomain(d.domain)">Remove</button></div>
        }
      }

      @if (section() === 'communities') {
        <h3>Interest communities</h3>
        <div class="bar">
          <input name="community" aria-label="Name of the new interest community" placeholder="Name (3 to 50 characters)" [(ngModel)]="community" />
          <button type="button" (click)="createCommunity()">Create community</button>
        </div>
        <h3>Suggested by students</h3>
        @for (s of suggestions(); track s.id) {
          <div class="row suggestion">
            <span><strong>{{ s.name }}</strong> <small>suggested by {{ s.suggestedByName }}</small></span>
            <button type="button" class="btn-small primary" (click)="createFromSuggestion(s)">Create community</button>
            <button type="button" class="btn-small" (click)="dismissSuggestion(s)">Dismiss</button>
          </div>
        } @empty { <p class="empty">No suggestions waiting.</p> }
      }

      @if (section() === 'moderators') {
        <h3>Moderators</h3>
        <div class="bar">
          <input name="email" aria-label="Email of the student to make or remove as moderator" placeholder="Student email" [(ngModel)]="email" />
          <button type="button" (click)="setModerator(true)">Make moderator</button>
          <button type="button" (click)="setModerator(false)">Remove role</button>
        </div>
        @for (m of moderators(); track m.id) { <div class="row"><span>{{ m.displayName }} <small>{{ m.email }}</small></span></div> }
      }

      @if (section() === 'settings') {
        <h3>Settings</h3>
        @for (s of settings(); track s.name) {
          <div class="row">
            <label>{{ s.name }} ({{ s.unit }})
              <input type="number" [name]="s.name" [ngModel]="s.value" (ngModelChange)="edited[s.name] = $event" />
            </label>
            <button type="button" class="btn-small" (click)="saveSetting(s)">Save</button>
          </div>
        }
      }

      @if (section() === 'pilot') {
        <h3>Pilot measures</h3>
        <p class="actions"><button type="button" (click)="loadReport()">Show report</button>
          <a href="/api/admin/pilot-report.csv" download>Download for Student Affairs (no names)</a></p>
        @if (report(); as r) {
          <p>Pilot week {{ r.pilotWeek }}, {{ r.period.from }} to {{ r.period.to }}, {{ r.records }} records used. Cohort groups under 5 students are combined.</p>
          <table>
            <tr><th>Cohort</th><th>Students</th><th>Requests</th><th>Accepted in 7 days</th><th>Reports</th><th>Acknowledged in 48 h</th><th>Upheld per 100 active</th></tr>
            @for (g of r.groups; track g.cohort) {
              <tr><td>{{ g.cohort }}</td><td>{{ g.students }}</td><td>{{ g.requests_sent }}</td><td>{{ g.accepted_within_7_days_pct ?? '–' }}%</td>
                  <td>{{ g.safety_reports }}</td><td>{{ g.acknowledged_within_48h_pct ?? '–' }}%</td><td>{{ g.upheld_per_100_active ?? '–' }}</td></tr>
            }
          </table>
        }
      }
    </app-sections>
  `,
  styles: `textarea { display: block; width: 100%; max-width: 30rem; }`,
})
export class AdminHome implements OnInit {
  private readonly api = inject(AdminService);
  readonly message = signal('');
  readonly status = signal<Status | null>(null);
  readonly courses = signal<CourseRow[]>([]);
  readonly domains = signal<DomainRow[]>([]);
  readonly moderators = signal<{ id: number; email: string; displayName: string }[]>([]);
  readonly settings = signal<SettingRow[]>([]);
  readonly report = signal<PilotReport | null>(null);
  readonly suggestions = signal<SuggestionRow[]>([]);
  readonly section = signal('status');
  readonly sectionList = computed<Section[]>(() => [
    { id: 'status', label: 'System status' },
    { id: 'courses', label: 'Courses' },
    { id: 'domains', label: 'Email domains' },
    { id: 'communities', label: 'Communities', count: this.suggestions().length },
    { id: 'moderators', label: 'Moderators' },
    { id: 'settings', label: 'Settings' },
    { id: 'pilot', label: 'Pilot measures' },
  ]);
  code = '';
  title = '';
  csv = '';
  domain = '';
  community = '';
  email = '';
  edited: Record<string, number> = {};

  ngOnInit(): void {
    this.refresh();
  }
  refresh(): void {
    this.api.status().subscribe((s) => this.status.set(s));
    this.api.courses().subscribe((c) => this.courses.set(c));
    this.api.domains().subscribe((d) => this.domains.set(d));
    this.api.moderators().subscribe((m) => this.moderators.set(m));
    this.api.settings().subscribe((s) => this.settings.set(s));
    this.api.suggestions().subscribe((x) => this.suggestions.set(x));
  }
  private after = (r: { ok: boolean; message?: string }) => {
    this.message.set(r.message ?? (r.ok ? 'Done.' : 'That did not work.'));
    this.refresh();
  };
  addCourse(): void { this.api.addCourse(this.code, this.title).subscribe(this.after); }
  archiveCourse(code: string): void { this.api.archiveCourse(code).subscribe(this.after); }
  importCourses(): void { this.api.importCourses(this.csv).subscribe(this.after); }
  addDomain(): void { this.api.addDomain(this.domain).subscribe(this.after); }
  removeDomain(d: string): void { this.api.removeDomain(d).subscribe(this.after); }
  createCommunity(): void { this.api.createCommunity(this.community).subscribe(this.after); }
  createFromSuggestion(s: SuggestionRow): void { this.api.createFromSuggestion(s.id).subscribe(this.after); }
  dismissSuggestion(s: SuggestionRow): void { this.api.dismissSuggestion(s.id).subscribe(this.after); }
  setModerator(enable: boolean): void { this.api.setModerator(this.email, enable).subscribe(this.after); }
  saveSetting(s: SettingRow): void {
    this.api.updateSetting(s.name, Number(this.edited[s.name] ?? s.value)).subscribe(this.after);
  }
  loadReport(): void { this.api.pilotReport().subscribe((r) => this.report.set(r)); }
}
