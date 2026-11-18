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
            <select [name]="'d' + r.id" [(ngModel)]="form(r).decision">
              <option value="">Decision…</option>
              @for (d of decisions; track d) { <option [value]="d">{{ d }}</option> }
            </select>
            <select [name]="'a' + r.id" [(ngModel)]="form(r).action">
              <option value="">Action…</option>
              @for (a of actions; track a) { <option [value]="a">{{ a }}</option> }
            </select>
            <textarea [name]="'n' + r.id" rows="2" placeholder="Note (required)" [(ngModel)]="form(r).note"></textarea>
            <button type="submit" class="decide">Record decision</button>
          </form>
        }
        @if (errors()[r.id]) { <p class="error">{{ errors()[r.id] }}</p> }
      </article>
    } @empty { <p id="queue-empty">No open reports.</p> }

    <h3>Case summary for Student Affairs</h3>
    <p>Enter the number of an upheld report.</p>
    <input type="number" name="summaryId" [(ngModel)]="summaryId" />
    <button type="button" (click)="loadSummary()">Show summary</button>
    @if (summaryError()) { <p class="error">{{ summaryError() }}</p> }
    @if (summary()) { <pre>{{ summary() }}</pre> }
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
  summaryId: number | null = null;
  private forms: Record<number, { decision: string; action: string; note: string }> = {};

  ngOnInit(): void {
    this.load();
  }
  load(): void {
    this.api.queue().subscribe((r) => this.reports.set(r));
  }
  form(r: QueueReport) {
    return (this.forms[r.id] ??= { decision: '', action: '', note: '' });
  }
  acknowledge(r: QueueReport): void {
    this.api.acknowledge(r.id).subscribe(() => this.load());
  }
  decide(r: QueueReport): void {
    const f = this.form(r);
    this.api.decide(r.id, f.decision, f.action, f.note).subscribe((res) => {
      this.errors.update((e) => ({ ...e, [r.id]: res.ok ? '' : Object.values(res.errors ?? {}).join(' ') || (res.message ?? '') }));
      if (res.ok) this.load();
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
