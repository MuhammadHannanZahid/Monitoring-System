import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, OnInit, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { forkJoin, timer } from 'rxjs';
import { ApiService } from '../../core/api.service';
import { DashboardActivity, DashboardIncident, DashboardSummary } from '../../core/models';

@Component({
  selector: 'app-dashboard-page',
  imports: [DatePipe, DecimalPipe],
  templateUrl: './dashboard.html',
  styleUrl: './dashboard.scss',
})
export class DashboardPage implements OnInit {
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  readonly summary = signal<DashboardSummary | null>(null);
  readonly incidents = signal<DashboardIncident[]>([]);
  readonly activity = signal<DashboardActivity[]>([]);
  readonly loading = signal(true);
  readonly error = signal('');

  ngOnInit(): void {
    timer(0, 5000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((iteration) => this.loadDashboard(iteration === 0));
  }

  loadDashboard(showLoading = true): void {
    if (showLoading) this.loading.set(true);
    this.error.set('');
    forkJoin({
      summary: this.api.get<DashboardSummary>('/dashboard/summary'),
      incidents: this.api.get<DashboardIncident[]>('/dashboard/incidents'),
      activity: this.api.get<DashboardActivity[]>('/dashboard/activity'),
    }).subscribe({
      next: ({ summary, incidents, activity }) => {
        this.summary.set(summary.data);
        this.incidents.set(incidents.data);
        this.activity.set(activity.data);
        this.loading.set(false);
      },
      error: (error: unknown) => {
        this.error.set(ApiService.errorMessage(error));
        this.loading.set(false);
      },
    });
  }

  formatDuration(seconds: number | null): string {
    if (seconds === null) return 'Ongoing';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }
}
