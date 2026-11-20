import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { COHORTS, CourseOption, INTENTS, Profile, ProfilesService } from './profiles.service';

@Component({
  selector: 'app-profiles-home',
  imports: [FormsModule],
  template: `
    <h2>Your profile</h2>
    @if (!saved() && firstTime()) {
      <p class="notice">Choose what you are looking for and your cohort to get started. Everything else is optional.</p>
    }
    @if (message()) { <p class="notice" id="profile-message">{{ message() }}</p> }

    <form (ngSubmit)="save()">
      <label>I am looking for
        <select name="intent" [(ngModel)]="intent">
          <option value="">Choose…</option>
          @for (i of intents; track i) { <option [value]="i">{{ i }}</option> }
        </select>
      </label>
      @if (errors()['intent']) { <p class="error" role="alert">{{ errors()['intent'] }}</p> }

      <label>Cohort (used only for pilot reports, never shown to other students)
        <select name="cohort" [(ngModel)]="cohort">
          <option value="">Choose…</option>
          @for (c of cohorts; track c) { <option [value]="c">{{ c }}</option> }
        </select>
      </label>
      @if (errors()['cohort']) { <p class="error" role="alert">{{ errors()['cohort'] }}</p> }

      <label>Year of study (optional, private)
        <input type="number" name="year" min="1" max="8" [(ngModel)]="year" />
      </label>
      @if (errors()['yearOfStudy']) { <p class="error" role="alert">{{ errors()['yearOfStudy'] }}</p> }

      <h3>Courses</h3>
      <div class="chips">
        @for (c of courses(); track c) {
          <span class="chip">{{ c }} <button type="button" (click)="removeCourse(c)" aria-label="Remove {{ c }}">×</button></span>
        } @empty { <em>No courses added.</em> }
      </div>
      <input name="courseSearch" aria-label="Search the course list" placeholder="Search the course list" [ngModel]="courseQuery" (ngModelChange)="searchCourses($event)" />
      @for (o of options(); track o.code) {
        <button type="button" class="option" (click)="addCourse(o)">{{ o.code }} {{ o.name }}</button>
      }
      @if (errors()['courses']) { <p class="error" role="alert">{{ errors()['courses'] }}</p> }

      <h3>Interests (up to 20, 30 characters each)</h3>
      <div class="chips">
        @for (i of interests(); track i) {
          <span class="chip">{{ i }} <button type="button" (click)="removeInterest(i)" aria-label="Remove {{ i }}">×</button></span>
        } @empty { <em>No interests added.</em> }
      </div>
      <input name="newInterest" maxlength="30" aria-label="Add an interest" placeholder="Add an interest" [(ngModel)]="newInterest" (keydown.enter)="addInterest($event)" />
      <button type="button" (click)="addInterest()">Add</button>
      @if (errors()['interests']) { <p class="error" role="alert">{{ errors()['interests'] }}</p> }

      <p><button type="submit" class="save">Save profile</button></p>
    </form>

    <h3>Delete account</h3>
    <p>This removes your profile, connections, messages and notifications. Your posts stay and show "deleted student".</p>
    <input type="password" name="deletePassword" aria-label="Your password, to confirm deleting the account" placeholder="Enter your password" [(ngModel)]="deletePassword" />
    <button type="button" class="danger" (click)="deleteAccount()">Delete my account</button>
    @if (deleteMessage()) { <p class="error" role="alert">{{ deleteMessage() }}</p> }
  `,
  styles: `.chips { display: flex; gap: .4rem; flex-wrap: wrap; margin: .4rem 0; } .chip button { border: 0; background: none; padding: 0 .2rem; } .chip button:hover { background: none; color: var(--danger); } .error { color: #b00020; } .option { display: block; margin: .2rem 0; }`,
})
export class ProfilesHome implements OnInit {
  private readonly api = inject(ProfilesService);
  private readonly router = inject(Router);
  readonly intents = INTENTS;
  readonly cohorts = COHORTS;
  intent = '';
  cohort = '';
  year: number | null = null;
  newInterest = '';
  courseQuery = '';
  deletePassword = '';
  readonly courses = signal<string[]>([]);
  readonly interests = signal<string[]>([]);
  readonly options = signal<CourseOption[]>([]);
  readonly errors = signal<Record<string, string>>({});
  readonly message = signal('');
  readonly deleteMessage = signal('');
  readonly firstTime = signal(false);
  readonly saved = signal(false);

  ngOnInit(): void {
    this.api.load().subscribe((p) => {
      this.firstTime.set(p === null);
      if (p) {
        this.intent = p.intent;
        this.cohort = p.cohort;
        this.year = p.yearOfStudy;
        this.courses.set(p.courses);
        this.interests.set(p.interests);
      }
    });
  }

  searchCourses(q: string): void {
    this.courseQuery = q;
    if (!q.trim()) {
      this.options.set([]);
      return;
    }
    this.api.searchCourses(q).subscribe((list) => this.options.set(list.filter((c) => !this.courses().includes(c.code))));
  }
  addCourse(o: CourseOption): void {
    this.courses.update((l) => [...l, o.code]);
    this.options.set([]);
    this.courseQuery = '';
  }
  removeCourse(code: string): void {
    this.courses.update((l) => l.filter((c) => c !== code));
  }
  addInterest(event?: Event): void {
    event?.preventDefault();
    const text = this.newInterest.trim();
    if (!text) return;
    if (!this.interests().some((i) => i.toLowerCase() === text.toLowerCase())) this.interests.update((l) => [...l, text]);
    this.newInterest = '';
  }
  removeInterest(i: string): void {
    this.interests.update((l) => l.filter((x) => x !== i));
  }

  save(): void {
    const profile: Profile = {
      intent: this.intent,
      cohort: this.cohort,
      yearOfStudy: this.year ?? null,
      interests: this.interests(),
      courses: this.courses(),
    };
    this.api.save(profile).subscribe((r) => {
      this.errors.set(r.errors ?? {});
      this.message.set(r.ok ? 'Profile saved.' : (r.message ?? 'Please fix the items marked below.'));
      this.saved.set(r.ok);
      if (r.ok && this.firstTime()) this.router.navigateByUrl('/connections');
    });
  }

  deleteAccount(): void {
    this.api.deleteAccount(this.deletePassword).subscribe((r) => {
      if (r.ok) this.router.navigateByUrl('/sign-in');
      else this.deleteMessage.set(r.message ?? '');
    });
  }
}
