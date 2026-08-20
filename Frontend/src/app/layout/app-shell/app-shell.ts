import { Component, DestroyRef, inject, signal } from '@angular/core';
import { Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { finalize } from 'rxjs';
import { AuthService } from '../../services/auth.service';
import { RealtimeService } from '../../services/realtime.service';

@Component({
  selector: 'app-shell',
  imports: [RouterLink, RouterLinkActive, RouterOutlet],
  templateUrl: './app-shell.html',
})
export class AppShell {
  readonly auth = inject(AuthService);
  private readonly realtime = inject(RealtimeService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly router = inject(Router);
  readonly menuOpen = signal(false);
  readonly loggingOut = signal(false);

  constructor() {
    this.realtime.connect();
    this.destroyRef.onDestroy(() => this.realtime.disconnect());
  }

  closeMenu(): void {
    this.menuOpen.set(false);
  }

  logout(): void {
    this.loggingOut.set(true);
    this.auth
      .logout()
      .pipe(finalize(() => this.loggingOut.set(false)))
      .subscribe({
        next: () => {
          this.realtime.disconnect();
          void this.router.navigate(['/login']);
        },
        error: () => {
          this.realtime.disconnect();
          this.auth.user.set(null);
          void this.router.navigate(['/login']);
        },
      });
  }
}
