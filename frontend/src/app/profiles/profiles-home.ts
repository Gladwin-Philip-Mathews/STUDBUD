import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { CommunitiesService } from '../communities/communities.service';
import { Section, Sections } from '../shared/sections';
import { COHORTS, CourseOption, INTENTS, Profile, ProfilesService } from './profiles.service';

@Component({
  selector: 'app-profiles-home',
  imports: [FormsModule, Sections],
  template: `
    <div class="page-head">
      <h2>Your profile</h2>
      <p class="lead">What other students see helps them decide whether to connect with you.</p>
    </div>
    @if (!saved() && firstTime()) {
      <p class="notice">Choose what you are looking for and your cohort to get started. Everything else is optional.</p>
    }
    @if (message()) { <p class="notice" id="profile-message">{{ message() }}</p> }

    <app-sections [sections]="sectionList" [(active)]="section" label="Profile sections">
      @if (section() !== 'account' && section() !== 'suggest') {
      <form class="card" (ngSubmit)="save()">
        @if (section() === 'about') {
          <h3>About you</h3>
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
        }

        @if (section() === 'courses') {
          <h3>Courses</h3>
          <p class="hint">Adding a course puts you in that course's community.</p>
          <div class="chips">
            @for (c of courses(); track c) {
              <span class="chip">{{ c }} <button type="button" (click)="removeCourse(c)" aria-label="Remove {{ c }}">×</button></span>
            } @empty { <em>No courses added.</em> }
          </div>
          <input name="courseSearch" type="search" aria-label="Search the course list" placeholder="Search the course list" [ngModel]="courseQuery" (ngModelChange)="searchCourses($event)" />
          @for (o of options(); track o.code) {
            <button type="button" class="option" (click)="addCourse(o)">{{ o.code }} {{ o.name }}</button>
          }
          <p class="hint">Can't find your course? Ask the admin to add it.</p>
          @if (errors()['courses']) { <p class="error" role="alert">{{ errors()['courses'] }}</p> }
        }

        @if (section() === 'interests') {
          <h3>Interests</h3>
          <p class="hint">Up to 20, 30 characters each. They help us suggest students like you.</p>
          <div class="chips">
            @for (i of interests(); track i) {
              <span class="chip">{{ i }} <button type="button" (click)="removeInterest(i)" aria-label="Remove {{ i }}">×</button></span>
            } @empty { <em>No interests added.</em> }
          </div>
          <div class="bar">
            <input name="newInterest" maxlength="30" aria-label="Add an interest" placeholder="Add an interest" [(ngModel)]="newInterest" (keydown.enter)="addInterest($event)" />
            <button type="button" (click)="addInterest()">Add</button>
          </div>
          @if (errors()['interests']) { <p class="error" role="alert">{{ errors()['interests'] }}</p> }
          <p class="hint">Can't find a community for your interest? Ask the admin, or <button type="button" class="link" (click)="section.set('suggest')">suggest an interest</button>.</p>
        }

        <p><button type="submit" class="save">Save profile</button></p>
      </form>
      }

      @if (section() === 'suggest') {
        <div class="card">
          <h3>Suggest an interest</h3>
          <p class="hint">Interest communities are set up by the administrator. Tell us the one you want, for example "Movies", and the administrator will see it. Can't find yours? Ask the admin.</p>
          <div class="bar">
            <input name="suggestion" maxlength="50" aria-label="Interest or community you would like to see" placeholder="Interest or community name (3 to 50 characters)" [(ngModel)]="suggestion" (keydown.enter)="suggest($event)" />
            <button type="button" class="primary" (click)="suggest()">Suggest</button>
          </div>
          @if (suggestError()) { <p class="error" role="alert">{{ suggestError() }}</p> }
          @if (suggestDone()) { <p class="notice" role="status">{{ suggestDone() }}</p> }
        </div>
      }

      @if (section() === 'account') {
        <div class="card">
          <h3>Delete account</h3>
          <p>This removes your profile, connections, messages and notifications. Your posts stay and show "deleted student".</p>
          <input type="password" name="deletePassword" aria-label="Your password, to confirm deleting the account" placeholder="Enter your password" [(ngModel)]="deletePassword" />
          <p><button type="button" class="danger" (click)="deleteAccount()">Delete my account</button></p>
          @if (deleteMessage()) { <p class="error" role="alert">{{ deleteMessage() }}</p> }
        </div>
      }
    </app-sections>
  `,
  styles: `.option { display: block; margin: .2rem 0; text-align: left; } form { max-width: none; }`,
})
export class ProfilesHome implements OnInit {
  private readonly api = inject(ProfilesService);
  private readonly router = inject(Router);
  private readonly route = inject(ActivatedRoute);
  private readonly communitiesApi = inject(CommunitiesService);
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
  readonly section = signal('about');
  readonly sectionList: Section[] = [
    { id: 'about', label: 'About you' },
    { id: 'courses', label: 'Courses' },
    { id: 'interests', label: 'Interests' },
    { id: 'suggest', label: 'Suggest an interest' },
    { id: 'account', label: 'Delete account' },
  ];
  suggestion = '';
  readonly suggestError = signal('');
  readonly suggestDone = signal('');

  ngOnInit(): void {
    const wanted = this.route.snapshot.queryParamMap.get('section');
    if (wanted && this.sectionList.some((x) => x.id === wanted)) this.section.set(wanted);
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

  suggest(event?: Event): void {
    event?.preventDefault();
    this.suggestDone.set('');
    this.communitiesApi.suggestInterest(this.suggestion).subscribe((r) => {
      this.suggestError.set(r.ok ? '' : (r.errors?.['name'] ?? r.message ?? 'That did not work.'));
      if (r.ok) {
        this.suggestDone.set(r.message ?? 'Thanks.');
        this.suggestion = '';
      }
    });
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
