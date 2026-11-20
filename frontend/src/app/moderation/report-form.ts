import { Component, input, output, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { inject } from '@angular/core';
import { ModerationService, REPORT_REASONS } from './moderation.service';

/** Report option shown on posts, replies and received messages (FR-039, FR-053, FR-060). */
@Component({
  selector: 'app-report-form',
  imports: [FormsModule],
  template: `
    @if (!open()) {
      <button type="button" class="report" (click)="open.set(true)">Report</button>
    } @else {
      <form class="report-form" (ngSubmit)="submit()">
        <select name="reason" aria-label="Reason for the report" [(ngModel)]="reason">
          <option value="">Reason…</option>
          @for (r of reasons; track r) { <option [value]="r">{{ r }}</option> }
        </select>
        <textarea name="text" rows="2" maxlength="500" aria-label="Details (optional, up to 500 characters)" placeholder="Details (optional, up to 500 characters)" [(ngModel)]="text"></textarea>
        <button type="submit" class="send-report">Send report</button>
        <button type="button" (click)="open.set(false)">Cancel</button>
        @if (error()) { <p class="error" role="alert">{{ error() }}</p> }
      </form>
    }
    @if (done()) { <p class="notice" role="status">{{ done() }}</p> }
  `,
  styles: `.report-form { display: grid; gap: .3rem; max-width: 26rem; margin: .4rem 0; } .error { color: #b00020; }`,
})
export class ReportForm {
  private readonly api = inject(ModerationService);
  readonly itemType = input.required<string>();
  readonly itemId = input.required<number>();
  readonly sent = output<void>();
  readonly reasons = REPORT_REASONS;
  readonly open = signal(false);
  readonly error = signal('');
  readonly done = signal('');
  reason = '';
  text = '';

  submit(): void {
    this.api.report(this.itemType(), this.itemId(), this.reason, this.text).subscribe((r) => {
      if (r.ok) {
        this.open.set(false);
        this.done.set(r.message ?? 'Report sent.');
        this.sent.emit();
      } else {
        this.error.set(Object.values(r.errors ?? {}).join(' ') || r.message || 'The report could not be sent.');
      }
    });
  }
}
