import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router, RouterOutlet } from '@angular/router';
import { AuthService } from './auth/auth.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  protected readonly auth = inject(AuthService);
  protected readonly apiStatus = signal('checking...');

  ngOnInit(): void {
    this.http.get<{ status: string }>('/api/health').subscribe({
      next: (r) => this.apiStatus.set(r.status),
      error: () => this.apiStatus.set('unreachable')
    });
    this.auth.loadMe().subscribe();
  }

  protected signOut(): void {
    this.auth.signOut().subscribe(() => this.router.navigateByUrl('/sign-in'));
  }
}
