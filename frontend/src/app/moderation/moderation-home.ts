import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ACTIONS, DECISIONS, ModerationService, QueueReport } from './moderation.service';

@Component({
  selector: 'app-moderation-home',
  imports: [FormsModule],
  template: `
    <h2>Moderator queue</h2>
    <p>Open reports, oldest first. A report is overdue if it is not acknowledged within 36 hours.</p>
    @for (r of reports(); track r.id) {
      <article class="report" [class.overdue]="r.overdue">
        <h3>#{{ r.id }} {{ r.reason }} @if (r.overdue) { <span class="flag">OVERDUE</span> }</h3>
        <p>Reported by {{ r.reporter }} about {{ r.reportedStudent }} · {{ r.ageHours }} hours ago · {{ r.status }}</p>
        @if (r.text) { <p><em>"{{ r.text }}"</em></p> }
        @if (r.item?.text) {
          <blockquote>
            @if (r.item?.title) { <strong>{{ r.item?.title }}</strong><br /> }
            {{ r.item?.text }} <small>({{ r.itemType }}, {{ r.item?.status }})</small>
          </blockquote>
        } @else { <p>Reported item: {{ r.itemType }}</p> }

        @if (!r.acknowledgedAt) {
          <button type="button" class="ack" (click)="acknowledge(r)">Acknowledge</button>
        } @else {
          <form (ngSubmit)="decide(r)">
            <select [name]="'d' + r.id" aria-label="Decision" [(ngModel)]="form(r).decision">
              <option value="">Decision…</option>
              @for (d of decisions; track d) { <option [value]="d">{{ d }}</option> }
            </select>
            <select [name]="'a' + r.id" aria-label="Action" [(ngModel)]="form(r).action">
              <option value="">Action…</option>
              @for (a of actions; track a) { <option [value]="a">{{ a }}</option> }
            </select>
            <textarea [name]="'n' + r.id" rows="2" aria-label="Note (required)" placeholder="Note (required)" [(ngModel)]="form(r).note"></textarea>
            @if (form(r).decision === 'upheld') {
              <label class="check"><input type="checkbox" [name]="'e' + r.id" [(ngModel)]="form(r).escalate" /> Prepare a case summary for the Office of Student Affairs</label>
            }
            <button type="submit" class="decide">Record decision</button>
          </form>
        }
        @if (errors()[r.id]) { <p class="error" role="alert">{{ errors()[r.id] }}</p> }
      </article>
    } @empty { <p id="queue-empty">No open reports.</p> }
    @if (notice()) { <p class="notice" role="status">{{ notice() }}</p> }

    <h3>Case summary for Student Affairs</h3>
    <p>Enter the number of an upheld report. Only the reported item is included, never other messages.</p>
    <input type="number" name="summaryId" aria-label="Report number for the case summary" [(ngModel)]="summaryId" />
    <button type="button" (click)="loadSummary()">Show summary</button>
    @if (summaryError()) { <p class="error" role="alert">{{ summaryError() }}</p> }
    @if (summary()) { <pre>{{ summary() }}</pre> }

    <h3>Later note on a closed report</h3>
    <p>A closed report cannot be changed. A conduct decision returned by Student Affairs, or any follow-up, is added as a dated note.</p>
    <form (ngSubmit)="addNote()">
      <input type="number" name="noteId" aria-label="Report number for the later note" placeholder="Report number" [(ngModel)]="noteId" />
      <textarea name="laterNote" rows="2" maxlength="1000" aria-label="Later note (up to 1000 characters)" placeholder="Later note (up to 1000 characters)" [(ngModel)]="laterNote"></textarea>
      <button type="submit" class="add-note">Add note</button>
    </form>
    @if (noteError()) { <p class="error" role="alert">{{ noteError() }}</p> }
    @if (noteDone()) { <p class="notice" role="status">{{ noteDone() }}</p> }
  `,
  styles: `.overdue { border-left: 4px solid #b00020; padding-left: .6rem; } .flag { color: #b00020; font-size: .8em; } article { margin: .75rem 0; background: var(--white); border: 1px solid var(--line); border-radius: 10px; padding: .75rem 1rem; } textarea, select { display: block; margin: .3rem 0; } .error { color: #b00020; }`,
})
export class ModerationHome implements OnInit {
  private readonly api = inject(ModerationService);
  readonly decisions = DECISIONS;
  readonly actions = ACTIONS;
  readonly reports = signal<QueueReport[]>([]);
  readonly errors = signal<Record<number, string>>({});
  readonly summary = signal('');
  readonly summaryError = signal('');
  readonly notice = signal('');
  readonly noteError = signal('');
  readonly noteDone = signal('');
  summaryId: number | null = null;
  noteId: number | null = null;
  laterNote = '';
  private forms: Record<number, { decision: string; action: string; note: string; escalate: boolean }> = {};

  ngOnInit(): void {
    this.load();
  }
  load(): void {
    this.api.queue().subscribe((r) => this.reports.set(r));
  }
  form(r: QueueReport) {
    return (this.forms[r.id] ??= { decision: '', action: '', note: '', escalate: false });
  }
  acknowledge(r: QueueReport): void {
    this.api.acknowledge(r.id).subscribe(() => this.load());
  }
  decide(r: QueueReport): void {
    const f = this.form(r);
    this.api.decide(r.id, f.decision, f.action, f.note, f.decision === 'upheld' && f.escalate).subscribe((res) => {
      this.errors.update((e) => ({ ...e, [r.id]: res.ok ? '' : Object.values(res.errors ?? {}).join(' ') || (res.message ?? '') }));
      if (res.ok) {
        this.notice.set(res.message ?? 'Decision recorded.');
        if (res.data) {
          this.summaryId = r.id;
          this.summary.set(JSON.stringify(res.data, null, 2)); // DF-24, ready for Student Affairs
          this.summaryError.set('');
        }
        this.load();
      }
    });
  }
  addNote(): void {
    if (!this.noteId) {
      this.noteError.set('Enter the report number.');
      return;
    }
    this.api.addNote(this.noteId, this.laterNote).subscribe((res) => {
      this.noteError.set(res.ok ? '' : Object.values(res.errors ?? {}).join(' ') || (res.message ?? ''));
      this.noteDone.set(res.ok ? `Note added to report #${this.noteId}.` : '');
      if (res.ok) this.laterNote = '';
    });
  }
  loadSummary(): void {
    if (!this.summaryId) return;
    this.api.summary(this.summaryId).subscribe((r) => {
      this.summaryError.set(r.ok ? '' : Object.values(r.errors ?? {}).join(' ') || (r.message ?? ''));
      this.summary.set(r.ok ? JSON.stringify(r.data, null, 2) : '');
    });
  }
}
