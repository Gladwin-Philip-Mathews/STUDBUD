import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);
  protected readonly apiStatus = signal('checking...');

  ngOnInit(): void {
    this.http.get<{ status: string }>('/api/health').subscribe({
      next: (r) => this.apiStatus.set(r.status),
      error: () => this.apiStatus.set('unreachable')
    });
  }
}
