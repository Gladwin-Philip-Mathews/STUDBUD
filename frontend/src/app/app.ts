import { Component, OnInit, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { NavigationEnd, Router, RouterLink, RouterOutlet } from '@angular/router';
import { filter } from 'rxjs';
import { AuthService } from './auth/auth.service';
import { NotificationsService } from './notifications/notifications.service';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink],
  templateUrl: './app.html',
  styleUrl: './app.scss'
})
export class App implements OnInit {
  private readonly http = inject(HttpClient);
  private readonly router = inject(Router);
  protected readonly auth = inject(AuthService);
  protected readonly notifications = inject(NotificationsService);
  protected readonly apiStatus = signal('checking...');

  ngOnInit(): void {
    this.http.get<{ status: string }>('/api/health').subscribe({
      next: (r) => this.apiStatus.set(r.status),
      error: () => this.apiStatus.set('unreachable')
    });
    this.auth.loadMe().subscribe();
    // Unread count on every page (FR-080)
    this.router.events.pipe(filter((e) => e instanceof NavigationEnd)).subscribe(() => {
      if (this.auth.account()) this.notifications.refresh();
    });
  }

  protected signOut(): void {
    this.auth.signOut().subscribe(() => this.router.navigateByUrl('/sign-in'));
  }
}
