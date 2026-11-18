import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, catchError, map, of } from 'rxjs';

export interface OnboardingQuestion {
  week: number;
  text: string;
  choices: string[];
}

@Injectable({ providedIn: 'root' })
export class OnboardingService {
  private readonly http = inject(HttpClient);

  question(): Observable<OnboardingQuestion | null> {
    return this.http.get<{ question: OnboardingQuestion | null }>('/api/onboarding/question').pipe(
      map((r) => r.question),
      catchError(() => of(null))
    );
  }
  answer(answer: string): Observable<boolean> {
    return this.http.post('/api/onboarding/answer', { answer }).pipe(map(() => true), catchError(() => of(false)));
  }
}
