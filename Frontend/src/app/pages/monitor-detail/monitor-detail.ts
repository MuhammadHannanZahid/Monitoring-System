import { DatePipe, DecimalPipe } from '@angular/common';
import { Component, DestroyRef, inject, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { catchError, forkJoin, merge, of, Subject, switchMap, timer } from 'rxjs';
import { ApiService } from '../../core/api.service';
import {
  MonitorDetail,
  ResponseHistory,
  ResponseHistoryPoint,
  StatusHistory,
  StatusHistoryPoint,
} from '../../core/models';

@Component({
  selector: 'app-monitor-detail-page',
  imports: [DatePipe, DecimalPipe, RouterLink],
  templateUrl: './monitor-detail.html',
  styleUrl: './monitor-detail.scss',
})
export class MonitorDetailPage {
  private readonly route = inject(ActivatedRoute);
  private readonly api = inject(ApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly refresh = new Subject<void>();
  private readonly monitorId = this.route.snapshot.paramMap.get('id') ?? '';
  readonly backUrl = String(this.route.snapshot.data['backUrl']);
  readonly ranges = [
    { label: 'Week', days: 7 },
    { label: 'Month', days: 30 },
    { label: 'Year', days: 365 },
  ];
  readonly detail = signal<MonitorDetail | null>(null);
  readonly statusHistory = signal<StatusHistoryPoint[]>([]);
  readonly responseHistory = signal<ResponseHistoryPoint[]>([]);
  readonly statusDays = signal(7);
  readonly responseDays = signal(7);
  readonly loading = signal(true);
  readonly error = signal('');

  constructor() {
    merge(timer(0, 5000), this.refresh)
      .pipe(
        switchMap(() =>
          forkJoin({
            detail: this.api.get<MonitorDetail>(`/dashboard/monitors/${this.monitorId}`),
            status: this.api.get<StatusHistory>(
              `/dashboard/status-history/${this.monitorId}?days=${this.statusDays()}`,
            ),
            response: this.api.get<ResponseHistory>(
              `/dashboard/response-history/${this.monitorId}?days=${this.responseDays()}`,
            ),
          }).pipe(
            catchError((error: unknown) => {
              this.error.set(ApiService.errorMessage(error));
              this.loading.set(false);
              return of(null);
            }),
          ),
        ),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((result) => {
        if (result === null) return;
        this.detail.set(result.detail.data);
        this.statusHistory.set(result.status.data.history);
        this.responseHistory.set(result.response.data.points);
        this.error.set('');
        this.loading.set(false);
      });
  }

  setStatusRange(days: number): void {
    this.statusDays.set(days);
    this.refresh.next();
  }

  setResponseRange(days: number): void {
    this.responseDays.set(days);
    this.refresh.next();
  }

  statusPolyline(): string {
    return this.polyline(this.statusHistory(), (point) => {
      if (point.status === 'up') return 20;
      if (point.status === 'down') return 120;
      return 70;
    });
  }

  responsePolyline(): string {
    const points = this.responseHistory().filter(
      (point): point is ResponseHistoryPoint & { response_time_ms: number } =>
        point.response_time_ms !== null,
    );
    const maximum = Math.max(...points.map((point) => point.response_time_ms), 1);
    return this.polyline(points, (point) => 125 - (point.response_time_ms / maximum) * 105);
  }

  maximumResponseTime(): number {
    return Math.max(...this.responseHistory().map((point) => point.response_time_ms ?? 0), 0);
  }

  firstDate(points: Array<StatusHistoryPoint | ResponseHistoryPoint>): string | null {
    return points[0]?.checked_at ?? null;
  }

  lastDate(points: Array<StatusHistoryPoint | ResponseHistoryPoint>): string | null {
    return points.at(-1)?.checked_at ?? null;
  }

  formatDuration(totalSeconds: number): string {
    if (totalSeconds < 60) return `${totalSeconds}s`;
    if (totalSeconds < 3600) return `${Math.floor(totalSeconds / 60)}m ${totalSeconds % 60}s`;
    if (totalSeconds < 86400)
      return `${Math.floor(totalSeconds / 3600)}h ${Math.floor((totalSeconds % 3600) / 60)}m`;
    return `${Math.floor(totalSeconds / 86400)}d ${Math.floor((totalSeconds % 86400) / 3600)}h`;
  }

  private polyline<T>(points: T[], yValue: (point: T) => number): string {
    if (!points.length) return '';
    const width = 760;
    return points
      .map((point, index) => {
        const x = points.length === 1 ? width / 2 : (index / (points.length - 1)) * width;
        return `${x.toFixed(1)},${yValue(point).toFixed(1)}`;
      })
      .join(' ');
  }
}
