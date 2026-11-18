import { Component, OnInit, inject, signal } from '@angular/core';
import { OnboardingQuestion, OnboardingService } from './onboarding.service';

/** FR-090: asked in the first week and again in week 12. The student can skip. */
@Component({
  selector: 'app-onboarding-question',
  template: `
    @if (question(); as q) {
      <section class="onboarding" id="onboarding">
        <p><strong>{{ q.text }}</strong></p>
        @for (c of q.choices; track c) { <button type="button" (click)="answer(c)">{{ c }}</button> }
        <button type="button" class="skip" (click)="answer('skipped')">Skip</button>
      </section>
    }
  `,
  styles: `button { margin-right: .4rem; }`,
})
export class OnboardingQuestionCard implements OnInit {
  private readonly api = inject(OnboardingService);
  readonly question = signal<OnboardingQuestion | null>(null);

  ngOnInit(): void {
    this.api.question().subscribe((q) => this.question.set(q));
  }
  answer(value: string): void {
    this.api.answer(value).subscribe(() => this.question.set(null));
  }
}
