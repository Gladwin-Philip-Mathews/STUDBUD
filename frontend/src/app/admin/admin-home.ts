import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AdminService, CourseRow, DomainRow, PilotReport, SettingRow, Status } from './admin.service';

@Component({
  selector: 'app-admin-home',
  imports: [FormsModule],
  template: `
    <h2>Administration</h2>
    @if (message()) { <p class="notice" id="admin-message">{{ message() }}</p> }

    <h3>System status</h3>
    @if (status(); as s) {
      <ul>
        <li>Accounts: {{ s.accounts }}</li>
        <li>Active users, last 7 days: {{ s.activeUsers }}</li>
        <li>Posts: {{ s.posts }}</li>
        <li>Open reports: {{ s.openReports }}</li>
        <li>Failed email messages: {{ s.failedEmails }}</li>
      </ul>
    }

    <h3>Courses</h3>
    <div class="bar">
      <input name="code" placeholder="Code, e.g. SWEN-261" [(ngModel)]="code" />
      <input name="title" placeholder="Title" [(ngModel)]="title" />
      <button type="button" class="add-course" (click)="addCourse()">Add course</button>
    </div>
    <textarea name="csv" rows="3" placeholder="Import: one course per line as code,title" [(ngModel)]="csv"></textarea>
    <button type="button" (click)="importCourses()">Import list</button>
    @for (c of courses(); track c.code) {
      <div class="row">{{ c.code }} {{ c.title }} <small>({{ c.status }})</small>
        @if (c.status === 'active') { <button type="button" (click)="archiveCourse(c.code)">Archive</button> }
      </div>
    }

    <h3>Accepted email domains</h3>
    <input name="domain" placeholder="g.rit.edu" [(ngModel)]="domain" />
    <button type="button" (click)="addDomain()">Add domain</button>
    @for (d of domains(); track d.domain) {
      <div class="row">{{ d.domain }} <button type="button" (click)="removeDomain(d.domain)">Remove</button></div>
    }

    <h3>Interest communities</h3>
    <input name="community" placeholder="Name (3 to 50 characters)" [(ngModel)]="community" />
    <button type="button" (click)="createCommunity()">Create community</button>

    <h3>Moderators</h3>
    <input name="email" placeholder="Student email" [(ngModel)]="email" />
    <button type="button" (click)="setModerator(true)">Make moderator</button>
    <button type="button" (click)="setModerator(false)">Remove role</button>
    @for (m of moderators(); track m.id) { <div class="row">{{ m.displayName }} ({{ m.email }})</div> }

    <h3>Settings</h3>
    @for (s of settings(); track s.name) {
      <div class="row">
        <label>{{ s.name }} ({{ s.unit }})
          <input type="number" [name]="s.name" [ngModel]="s.value" (ngModelChange)="edited[s.name] = $event" />
        </label>
        <button type="button" (click)="saveSetting(s)">Save</button>
      </div>
    }

    <h3>Pilot measures</h3>
    <p><button type="button" (click)="loadReport()">Show report</button>
      <a href="/api/admin/pilot-report.csv" download>Download for Student Affairs (no names)</a></p>
    @if (report(); as r) {
      <p>Pilot week {{ r.pilotWeek }}. Cohort groups under 5 students are combined.</p>
      <table>
        <tr><th>Cohort</th><th>Students</th><th>Requests</th><th>Accepted in 7 days</th><th>Reports</th><th>Acknowledged in 48 h</th><th>Upheld per 100 active</th></tr>
        @for (g of r.groups; track g.cohort) {
          <tr><td>{{ g.cohort }}</td><td>{{ g.students }}</td><td>{{ g.requests_sent }}</td><td>{{ g.accepted_within_7_days_pct ?? '–' }}%</td>
              <td>{{ g.safety_reports }}</td><td>{{ g.acknowledged_within_48h_pct ?? '–' }}%</td><td>{{ g.upheld_per_100_active ?? '–' }}</td></tr>
        }
      </table>
    }
  `,
  styles: `.bar, .row { display: flex; gap: .5rem; align-items: center; flex-wrap: wrap; margin: .3rem 0; } textarea { display: block; width: 100%; max-width: 30rem; } table { border-collapse: collapse; } td, th { border: 1px solid #ccc; padding: .25rem .5rem; }`,
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
  setModerator(enable: boolean): void { this.api.setModerator(this.email, enable).subscribe(this.after); }
  saveSetting(s: SettingRow): void {
    this.api.updateSetting(s.name, Number(this.edited[s.name] ?? s.value)).subscribe(this.after);
  }
  loadReport(): void { this.api.pilotReport().subscribe((r) => this.report.set(r)); }
}
